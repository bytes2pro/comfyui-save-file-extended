from __future__ import annotations

import hashlib
import io
import os

import av
import folder_paths
import torch
from server import PromptServer

from ..cloud import get_uploader


def f32_pcm(wav: torch.Tensor) -> torch.Tensor:
    """Convert audio to float 32 bits PCM format."""
    if wav.dtype.is_floating_point:
        return wav
    elif wav.dtype == torch.int16:
        return wav.float() / (2 ** 15)
    elif wav.dtype == torch.int32:
        return wav.float() / (2 ** 31)
    raise ValueError(f"Unsupported wav dtype: {wav.dtype}")

def load(filepath: str) -> tuple[torch.Tensor, int]:
    with av.open(filepath) as af:
        if not af.streams.audio:
            raise ValueError("No audio stream found in the file.")

        stream = af.streams.audio[0]
        sr = stream.codec_context.sample_rate
        n_channels = stream.channels

        frames = []
        length = 0
        for frame in af.decode(streams=stream.index):
            buf = torch.from_numpy(frame.to_ndarray())
            if buf.shape[0] != n_channels:
                buf = buf.view(-1, n_channels).t()

            frames.append(buf)
            length += buf.shape[1]

        if not frames:
            raise ValueError("No audio frames decoded.")

        wav = torch.cat(frames, dim=1)
        wav = f32_pcm(wav)
        return wav, sr


def load_from_bytes(raw: bytes) -> tuple[torch.Tensor, int]:
    with av.open(io.BytesIO(raw)) as af:
        if not af.streams.audio:
            raise ValueError("No audio stream found in the data.")

        stream = af.streams.audio[0]
        sr = stream.codec_context.sample_rate
        n_channels = stream.channels

        frames = []
        for frame in af.decode(streams=stream.index):
            buf = torch.from_numpy(frame.to_ndarray())
            if buf.shape[0] != n_channels:
                buf = buf.view(-1, n_channels).t()
            frames.append(buf)
        if not frames:
            raise ValueError("No audio frames decoded.")
        wav = torch.cat(frames, dim=1)
        wav = f32_pcm(wav)
        return wav, sr

class LoadAudioExtended:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = folder_paths.filter_files_content_types(os.listdir(input_dir), ["audio", "video"])
        return {
            "required": {
                "load_from_cloud": ("BOOLEAN", {"default": False, "socketless": True, "label_on": "Cloud", "label_off": "Local"}),
                "file_paths": ("STRING", {"multiline": True, "placeholder": "One filename per line"}),
                "local_file": (sorted(files), {"audio_upload": True}),
            },
            "optional": {
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
                "bucket_link": ("STRING", {"default": ""}),
                "cloud_folder_path": ("STRING", {"default": ""}),
                "cloud_api_key": ("STRING", {"default": ""}),
            },
        }

    CATEGORY = "audio"

    RETURN_TYPES = ("AUDIO", )
    FUNCTION = "load"

    def load(self, load_from_cloud: bool, file_paths: str, cloud_provider="AWS S3", bucket_link="", cloud_folder_path="", cloud_api_key="", local_file=None):
        def _notify(kind: str, payload: dict):
            try:
                PromptServer.instance.send_sync(
                    "comfyui.loadaudioextended.status",
                    {"phase": kind, **payload}
                )
            except Exception:
                pass

        paths = [p.strip() for p in str(file_paths or "").splitlines() if p.strip()]
        if not load_from_cloud and not paths and local_file:
            paths = [local_file]
        if not paths:
            raise ValueError("Provide at least one file path or select a local file")

        total = len(paths)
        _notify("start", {"total": total, "provider": cloud_provider if load_from_cloud else None})

        waveforms = []
        sample_rate = None

        if load_from_cloud:
            Uploader = get_uploader(cloud_provider)
            try:
                def _progress_cb(info: dict):
                    _notify("progress", {"where": "cloud", "current": (info.get("index", 0) + 1), "total": total, "filename": info.get("path"), "provider": cloud_provider})
                bytes_done = {"n": 0}
                def _bytes_cb(info: dict):
                    delta = int(info.get("delta") or 0)
                    bytes_done["n"] += delta
                    _notify("progress", {"where": "cloud", "bytes_done": bytes_done["n"], "filename": info.get("filename"), "provider": cloud_provider})
                try:
                    results = Uploader.download_many(paths, bucket_link, cloud_folder_path, cloud_api_key, _progress_cb, _bytes_cb)
                except TypeError:
                    results = Uploader.download_many(paths, bucket_link, cloud_folder_path, cloud_api_key, _progress_cb)
            except Exception as e:
                _notify("error", {"message": str(e)})
                raise RuntimeError(f"Cloud download failed: {e}")

            for res in results:
                wav, sr = load_from_bytes(res["content"])  # type: ignore[index]
                waveforms.append(wav.unsqueeze(0))
                sample_rate = sr
                _notify("progress", {"where": "cloud", "current": len(waveforms), "total": total, "filename": res.get("filename"), "provider": cloud_provider})
        else:
            input_dir = folder_paths.get_input_directory()
            for rel in paths:
                audio_path = os.path.join(input_dir, rel)
                if not os.path.isfile(audio_path):
                    raise FileNotFoundError(audio_path)
                wav, sr = load(audio_path)
                waveforms.append(wav.unsqueeze(0))
                sample_rate = sr
                _notify("progress", {"where": "local", "current": len(waveforms), "total": total, "filename": rel})

        if len(waveforms) > 1:
            # Try concat on time dim only when channels match
            ch = waveforms[0].shape[1]
            if all(w.shape[1] == ch for w in waveforms):
                out_wav = torch.cat(waveforms, dim=0)
            else:
                out_wav = waveforms[0]
        else:
            out_wav = waveforms[0]

        _notify("complete", {"count": len(waveforms), "provider": cloud_provider if load_from_cloud else None})
        return ({"waveform": out_wav, "sample_rate": int(sample_rate or 48000)}, )

    @classmethod
    def IS_CHANGED(s, load_from_cloud, file_paths, cloud_provider="AWS S3", bucket_link="", cloud_folder_path="", cloud_api_key="", local_file=None):
        m = hashlib.sha256()
        for part in [str(load_from_cloud), str(file_paths), str(cloud_provider), str(bucket_link), str(cloud_folder_path), str(local_file)]:
            m.update(part.encode("utf-8"))
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(s, load_from_cloud, file_paths, cloud_provider="AWS S3", bucket_link="", cloud_folder_path="", cloud_api_key="", local_file=None):
        if (not file_paths or not str(file_paths).strip()) and load_from_cloud:
            return "Provide one or more file paths (one per line)."
        if load_from_cloud:
            if not (cloud_provider and str(cloud_provider).strip()):
                return "Cloud: 'cloud_provider' is required."
            if not (bucket_link and bucket_link.strip()):
                return "Cloud: 'bucket_link' is required."
            if not (cloud_api_key and cloud_api_key.strip()):
                return "Cloud: 'cloud_api_key' is required."
        return True