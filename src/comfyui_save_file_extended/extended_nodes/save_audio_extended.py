from __future__ import annotations

import io
import json
import os
from typing import Literal
from uuid import uuid4

import av
import folder_paths
import torch
import torchaudio
from comfy.cli_args import args
from comfy.comfy_types import FileLocator
from server import PromptServer

from ..cloud import get_uploader


class SaveAudioExtended:
    """
    Save audio locally and/or upload to a cloud provider.

    - Local: Writes files under the ComfyUI output directory when enabled.
    - Cloud: Uploads all rendered files in one batch when enabled.
    - Formats: wav, flac, mp3, opus.
    """

    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type: Literal["output"] = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio": ("AUDIO", {"tooltip": "Audio dict with 'waveform' [B,C,T] and 'sample_rate'."}),
                "filename_prefix": ("STRING", {"default": "audio/ComfyUI", "tooltip": "Filename prefix. Supports tokens like %date:yyyy-MM-dd%."}),
                "format": (["wav", "flac", "mp3", "opus"], {"default": "flac"}),
            },
            "optional": {
                # Quality settings (interpretation depends on format)
                "quality": (["V0", "64k", "96k", "128k", "192k", "320k"], {"default": "128k", "tooltip": "For mp3/opus, selects bitrate or VBR preset. Ignored for wav/flac."}),
                # Cloud section
                "save_to_cloud": ("BOOLEAN", {"default": False, "socketless": True, "label_on": "Enabled", "label_off": "Disabled"}),
                "cloud_provider": ([
                    "AWS S3",
                    "Google Cloud Storage",
                    "Azure Blob Storage",
                    "Backblaze B2",
                    "Google Drive",
                    "Dropbox",
                    "OneDrive",
                    "FTP",
                    "Supabase Storage",
                    "UploadThing",
                    "S3-Compatible"
                ], {"default": "AWS S3"}),
                "bucket_link": ("STRING", {"default": "", "placeholder": "Bucket URL / Conn String"}),
                "cloud_folder_path": ("STRING", {"default": "outputs"}),
                "cloud_api_key": ("STRING", {"default": ""}),
                # Local section
                "save_to_local": ("BOOLEAN", {"default": True, "socketless": True, "label_on": "Enabled", "label_off": "Disabled"}),
                "local_folder_path": ("STRING", {"default": ""}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_audio"
    OUTPUT_NODE = True
    CATEGORY = "audio"

    @classmethod
    def VALIDATE_INPUTS(s,
        audio,
        filename_prefix="ComfyUI",
        format="flac",
        quality="128k",
        save_to_cloud=False,
        cloud_provider="AWS S3",
        bucket_link="",
        cloud_folder_path="outputs",
        cloud_api_key="",
        save_to_local=True,
        local_folder_path="",
        prompt=None,
        extra_pnginfo=None,
    ):
        fmt = (str(format) if format is not None else "").lower()
        q = str(quality) if quality is not None else ""
        if fmt == "mp3":
            allowed_mp3 = {"V0", "128k", "320k"}
            if q and q not in allowed_mp3:
                return "For MP3, quality must be one of: V0, 128k, 320k."
        if fmt == "opus":
            allowed_opus = {"64k", "96k", "128k", "192k", "320k"}
            if q and q not in allowed_opus:
                return "For Opus, quality must be one of: 64k, 96k, 128k, 192k, 320k."
        if not save_to_cloud and not save_to_local:
            return "Enable at least one of 'Save to Cloud' or 'Save to Local'."
        if save_to_cloud:
            if not (cloud_provider and str(cloud_provider).strip()):
                return "Cloud: 'cloud_provider' is required."
            if not (bucket_link and bucket_link.strip()):
                return "Cloud: 'bucket_link' is required."
            if not (cloud_api_key and cloud_api_key.strip()):
                return "Cloud: 'cloud_api_key' is required."
        return True

    def _encode_one(self, waveform, sample_rate: int, fmt: str, quality: str, metadata: dict) -> bytes:
        # Prepare format-specific settings
        fmt = fmt.lower()
        output_buffer = io.BytesIO()

        # Adjust sample rate for Opus
        if fmt == "opus":
            OPUS_RATES = [8000, 12000, 16000, 24000, 48000]
            target_sr = sample_rate
            if target_sr > 48000:
                target_sr = 48000
            if target_sr not in OPUS_RATES:
                for rate in sorted(OPUS_RATES):
                    if rate >= target_sr:
                        target_sr = rate
                        break
                if target_sr not in OPUS_RATES:
                    target_sr = 48000
            if target_sr != sample_rate:
                waveform = torchaudio.functional.resample(waveform, sample_rate, target_sr)
            sample_rate = target_sr

        # Prepare container and stream
        container = av.open(output_buffer, mode='w', format=fmt)
        for k, v in metadata.items():
            container.metadata[k] = v

        channels = int(waveform.shape[0])
        layout = 'mono' if channels == 1 else 'stereo'

        if fmt == "mp3":
            stream = container.add_stream("libmp3lame", rate=sample_rate)
            if quality == "V0":
                stream.codec_context.qscale = 1
            elif quality == "128k":
                stream.bit_rate = 128000
            elif quality == "192k":
                stream.bit_rate = 192000
            elif quality == "320k":
                stream.bit_rate = 320000
            frame = av.AudioFrame.from_ndarray(waveform.movedim(0, 1).contiguous().float().numpy(), format='flt', layout=layout)
        elif fmt == "opus":
            stream = container.add_stream("libopus", rate=sample_rate)
            # Map quality choices to bitrates (match core nodes: 64k/96k/128k/192k/320k)
            if quality == "64k":
                stream.bit_rate = 64000
            elif quality == "96k":
                stream.bit_rate = 96000
            elif quality == "128k":
                stream.bit_rate = 128000
            elif quality == "192k":
                stream.bit_rate = 192000
            elif quality == "320k":
                stream.bit_rate = 320000
            frame = av.AudioFrame.from_ndarray(waveform.movedim(0, 1).contiguous().float().numpy(), format='flt', layout=layout)
        elif fmt == "wav":
            stream = container.add_stream("pcm_s16le", rate=sample_rate)
            # Convert float [-1,1] to int16
            pcm = (waveform.clamp(-1, 1) * 32767.0).round().to(dtype=torch.int16)
            frame = av.AudioFrame.from_ndarray(pcm.movedim(0, 1).contiguous().numpy(), format='s16', layout=layout)
        else:  # flac
            stream = container.add_stream("flac", rate=sample_rate)
            frame = av.AudioFrame.from_ndarray(waveform.movedim(0, 1).contiguous().float().numpy(), format='flt', layout=layout)

        frame.sample_rate = sample_rate
        frame.pts = 0
        container.mux(stream.encode(frame))
        container.mux(stream.encode(None))
        container.close()
        output_buffer.seek(0)
        return output_buffer.getvalue()

    def save_audio(self, audio, filename_prefix="ComfyUI", format="flac", quality="128k", save_to_cloud=False, cloud_provider="AWS S3", bucket_link="", cloud_folder_path="outputs", cloud_api_key="", save_to_local=True, local_folder_path="", prompt=None, extra_pnginfo=None):
        def _notify(kind: str, payload: dict):
            try:
                PromptServer.instance.send_sync(
                    "comfyui.saveaudioextended.status",
                    {"phase": kind, **payload}
                )
            except Exception:
                pass

        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir)

        # Resolve local save directory
        local_save_dir = full_output_folder
        ui_subfolder = subfolder
        if save_to_local:
            local_save_dir = os.path.join(full_output_folder, local_folder_path or "")
            try:
                os.makedirs(local_save_dir, exist_ok=True)
            except Exception:
                local_save_dir = full_output_folder
            ui_subfolder = os.path.join(subfolder, local_folder_path) if subfolder else local_folder_path

        results: list[FileLocator] = []
        cloud_results = []
        cloud_items = []

        metadata = {}
        if not args.disable_metadata:
            if prompt is not None:
                metadata["prompt"] = json.dumps(prompt)
            if extra_pnginfo is not None:
                for x in extra_pnginfo:
                    metadata[str(x)] = json.dumps(extra_pnginfo[x])

        wave_batch = audio["waveform"].cpu()
        sample_rate = int(audio["sample_rate"])  # type: ignore
        total = int(wave_batch.shape[0])
        _notify("start", {"total": total, "provider": cloud_provider if save_to_cloud else None})

        for (batch_number, waveform) in enumerate(wave_batch):
            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            fmt = str(format).lower()
            file = f"{filename_with_batch_num}-{uuid4()}.{fmt}"

            # Encode to bytes once
            try:
                audio_bytes = self._encode_one(waveform, sample_rate, fmt, str(quality), metadata)
            except Exception as e:
                _notify("error", {"message": str(e)})
                raise

            if save_to_local:
                try:
                    with open(os.path.join(local_save_dir, file), "wb") as f:
                        f.write(audio_bytes)
                    results.append({
                        "filename": file,
                        "subfolder": ui_subfolder,
                        "type": self.type
                    })
                    _notify("progress", {"where": "local", "current": counter, "total": total, "filename": file})
                except Exception as e:
                    _notify("error", {"message": str(e)})

            if save_to_cloud:
                cloud_items.append({"filename": file, "content": audio_bytes})

            counter += 1

        if save_to_cloud and cloud_items:
            try:
                Uploader = get_uploader(cloud_provider)
                sent_bytes = {"n": 0}
                def _bytes_cb(info: dict):
                    delta = int(info.get("delta") or 0)
                    sent_bytes["n"] += delta
                    _notify("progress", {"where": "cloud", "bytes_done": sent_bytes["n"], "bytes_total": sum(len(it["content"]) for it in cloud_items), "filename": info.get("filename"), "provider": cloud_provider})
                def _progress_cb(info: dict):
                    _notify("progress", {"where": "cloud", "current": (info.get("index", 0) + 1), "total": len(cloud_items), "filename": info.get("path"), "provider": cloud_provider})
                try:
                    cloud_results = Uploader.upload_many(cloud_items, bucket_link, cloud_folder_path, cloud_api_key, _progress_cb, _bytes_cb)
                except TypeError:
                    cloud_results = Uploader.upload_many(cloud_items, bucket_link, cloud_folder_path, cloud_api_key, _progress_cb)
            except Exception as e:
                _notify("error", {"message": str(e)})
            else:
                _notify("complete", {"count_local": len(results), "count_cloud": len(cloud_results), "provider": cloud_provider})
        else:
            _notify("complete", {"count_local": len(results), "count_cloud": 0, "provider": None})

        return {"ui": {"audio": results}, "cloud": cloud_results}


class SaveAudioMP3Extended:
    def __init__(self):
        self._impl = SaveAudioExtended()
        self.output_dir = self._impl.output_dir
        self.type = self._impl.type
        self.prefix_append = self._impl.prefix_append

    @classmethod
    def INPUT_TYPES(s):
        spec = SaveAudioExtended.INPUT_TYPES()
        # Lock format to mp3 by default
        spec["required"]["format"] = (["mp3"], {"default": "mp3"})
        # Match core node: MP3 quality options
        spec["optional"]["quality"] = (["V0", "128k", "320k"], {"default": "V0"})
        return spec

    RETURN_TYPES = ()
    FUNCTION = "save_audio"
    OUTPUT_NODE = True
    CATEGORY = "audio"

    def save_audio(self, *args, **kwargs):  # type: ignore
        kwargs["format"] = "mp3"
        return self._impl.save_audio(*args, **kwargs)


class SaveAudioOpusExtended:
    def __init__(self):
        self._impl = SaveAudioExtended()
        self.output_dir = self._impl.output_dir
        self.type = self._impl.type
        self.prefix_append = self._impl.prefix_append

    @classmethod
    def INPUT_TYPES(s):
        spec = SaveAudioExtended.INPUT_TYPES()
        # Lock format to opus by default and expose bitrate options
        spec["required"]["format"] = (["opus"], {"default": "opus"})
        spec["optional"]["quality"] = (["64k", "96k", "128k", "192k", "320k"], {"default": "128k"})
        return spec

    RETURN_TYPES = ()
    FUNCTION = "save_audio"
    OUTPUT_NODE = True
    CATEGORY = "audio"

    def save_audio(self, *args, **kwargs):  # type: ignore
        kwargs["format"] = "opus"
        return self._impl.save_audio(*args, **kwargs)