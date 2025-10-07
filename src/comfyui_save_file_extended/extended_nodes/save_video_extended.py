from __future__ import annotations

import json
import os
from fractions import Fraction
from typing import Literal
from uuid import uuid4

import av
import folder_paths
import torch
from comfy.cli_args import args
from comfy.comfy_types import IO, ComfyNodeABC, FileLocator
from comfy_api.latest import Input, Types
from server import PromptServer

from ..cloud import get_uploader


class SaveWEBMExtended:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename_prefix": ("STRING", {"default": "video/ComfyUI"}),
                "codec": (["vp9", "av1"], {}),
                "fps": ("FLOAT", {"default": 24.0, "min": 0.01, "max": 1000.0, "step": 0.01}),
                "crf": ("FLOAT", {"default": 32.0, "min": 0, "max": 63.0, "step": 1, "tooltip": "Higher crf means lower quality with a smaller file size, lower crf means higher quality higher filesize."}),
            },
            "optional": {
                "custom_filename": ("STRING", {"default": "", "placeholder": "Custom filename (optional)", "tooltip": "Custom filename for saved video. If empty, uses the default filename generation with prefix and UUID. Do not include file extension."}),
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
                "bucket_link": ("STRING", {"default": ""}),
                "cloud_folder_path": ("STRING", {"default": "outputs"}),
                "cloud_api_key": ("STRING", {"default": ""}),
                "save_to_local": ("BOOLEAN", {"default": True, "socketless": True, "label_on": "Enabled", "label_off": "Disabled"}),
                "local_folder_path": ("STRING", {"default": ""}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filenames",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "save_images"

    OUTPUT_NODE = True

    CATEGORY = "image/video"

    EXPERIMENTAL = True

    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        save_to_cloud = kwargs.get("save_to_cloud", False)
        save_to_local = kwargs.get("save_to_local", True)
        cloud_provider = kwargs.get("cloud_provider", "AWS S3")
        bucket_link = kwargs.get("bucket_link", "")
        cloud_api_key = kwargs.get("cloud_api_key", "")
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

    def save_images(self, images, codec, fps, filename_prefix, crf, custom_filename="", prompt=None, extra_pnginfo=None, save_to_cloud=False, cloud_provider="AWS S3", bucket_link="", cloud_folder_path="outputs", cloud_api_key="", save_to_local=True, local_folder_path=""):
        def _notify(kind: str, payload: dict):
            try:
                PromptServer.instance.send_sync(
                    "comfyui.savevideoextended.status",
                    {"phase": kind, **payload}
                )
            except Exception:
                pass

        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])

        # Resolve local save directory and UI subfolder
        local_save_dir = full_output_folder
        ui_subfolder = subfolder
        if save_to_local:
            local_save_dir = os.path.join(full_output_folder, local_folder_path or "")
            try:
                os.makedirs(local_save_dir, exist_ok=True)
            except Exception:
                local_save_dir = full_output_folder
            ui_subfolder = os.path.join(subfolder, local_folder_path) if subfolder else local_folder_path

        # Use custom filename if provided, otherwise use default filename generation
        if custom_filename and custom_filename.strip():
            file = f"{custom_filename.strip()}.webm"
        else:
            file = f"{filename}-{uuid4()}.webm"
        out_path = os.path.join(local_save_dir, file)

        _notify("start", {"total": 1, "provider": cloud_provider if save_to_cloud else None})
        filenames: list[str] = []

        container = av.open(out_path, mode="w")
        if prompt is not None:
            container.metadata["prompt"] = json.dumps(prompt)
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                container.metadata[x] = json.dumps(extra_pnginfo[x])
        codec_map = {"vp9": "libvpx-vp9", "av1": "libsvtav1"}
        stream = container.add_stream(codec_map[codec], rate=Fraction(round(fps * 1000), 1000))
        stream.width = images.shape[-2]
        stream.height = images.shape[-3]
        stream.pix_fmt = "yuv420p10le" if codec == "av1" else "yuv420p"
        stream.bit_rate = 0
        stream.options = {'crf': str(crf)}
        if codec == "av1":
            stream.options["preset"] = "6"
        for frame in images:
            frame = av.VideoFrame.from_ndarray(torch.clamp(frame[..., :3] * 255, min=0, max=255).to(device=torch.device("cpu"), dtype=torch.uint8).numpy(), format="rgb24")
            for packet in stream.encode(frame):
                container.mux(packet)
        container.mux(stream.encode())
        container.close()

        results: list[FileLocator] = []
        cloud_results = []
        if save_to_local:
            results.append({
                "filename": file,
                "subfolder": ui_subfolder,
                "type": self.type
            })
            _notify("progress", {"where": "local", "current": 1, "total": 1, "filename": file})
        filenames.append(file)

        if save_to_cloud:
            try:
                with open(out_path, "rb") as f:
                    data = f.read()
                Uploader = get_uploader(cloud_provider)
                sent_bytes = {"n": 0}
                def _bytes_cb(info: dict):
                    delta = int(info.get("delta") or 0)
                    sent_bytes["n"] += delta
                    _notify("progress", {"where": "cloud", "bytes_done": sent_bytes["n"], "bytes_total": len(data), "filename": info.get("filename"), "provider": cloud_provider})
                def _progress_cb(info: dict):
                    _notify("progress", {"where": "cloud", "current": (info.get("index", 0) + 1), "total": 1, "filename": info.get("path"), "provider": cloud_provider})
                try:
                    cloud_results = Uploader.upload_many([{"filename": file, "content": data}], bucket_link, cloud_folder_path, cloud_api_key, _progress_cb, _bytes_cb)
                except TypeError:
                    cloud_results = Uploader.upload_many([{"filename": file, "content": data}], bucket_link, cloud_folder_path, cloud_api_key, _progress_cb)
            except Exception as e:
                _notify("error", {"message": str(e)})
            else:
                _notify("complete", {"count_local": len(results), "count_cloud": len(cloud_results), "provider": cloud_provider})
        else:
            _notify("complete", {"count_local": len(results), "count_cloud": 0, "provider": None})

        # If local is disabled, remove the temp file
        if not save_to_local:
            try:
                os.remove(out_path)
            except Exception:
                pass

        return {"ui": {"images": results, "animated": (True,)}, "result": (filenames,), "cloud": cloud_results}


class SaveVideoExtended(ComfyNodeABC):
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type: Literal["output"] = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": (IO.VIDEO, {"tooltip": "The video to save."}),
                "filename_prefix": ("STRING", {"default": "video/ComfyUI", "tooltip": "The prefix for the file to save. This may include formatting information such as %date:yyyy-MM-dd% or %Empty Latent Image.width% to include values from nodes."}),
                "format": (Types.VideoContainer.as_input(), {"default": "auto", "tooltip": "The format to save the video as."}),
                "codec": (Types.VideoCodec.as_input(), {"default": "auto", "tooltip": "The codec to use for the video."}),
            },
            "optional": {
                "custom_filename": ("STRING", {"default": "", "placeholder": "Custom filename (optional)", "tooltip": "Custom filename for saved video. If empty, uses the default filename generation with prefix and UUID. Do not include file extension."}),
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
                "bucket_link": ("STRING", {"default": ""}),
                "cloud_folder_path": ("STRING", {"default": "outputs"}),
                "cloud_api_key": ("STRING", {"default": ""}),
                "save_to_local": ("BOOLEAN", {"default": True, "socketless": True, "label_on": "Enabled", "label_off": "Disabled"}),
                "local_folder_path": ("STRING", {"default": ""}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filenames",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "save_video"

    OUTPUT_NODE = True

    CATEGORY = "image/video"
    DESCRIPTION = "Saves the input images to your ComfyUI output directory."

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        save_to_cloud = kwargs.get("save_to_cloud", False)
        save_to_local = kwargs.get("save_to_local", True)
        cloud_provider = kwargs.get("cloud_provider", "AWS S3")
        bucket_link = kwargs.get("bucket_link", "")
        cloud_api_key = kwargs.get("cloud_api_key", "")
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

    def save_video(self, video: Input.Video, filename_prefix, format, codec, custom_filename="", save_to_cloud=False, cloud_provider="AWS S3", bucket_link="", cloud_folder_path="outputs", cloud_api_key="", save_to_local=True, local_folder_path="", prompt=None, extra_pnginfo=None):
        def _notify(kind: str, payload: dict):
            try:
                PromptServer.instance.send_sync(
                    "comfyui.savevideoextended.status",
                    {"phase": kind, **payload}
                )
            except Exception:
                pass
        filename_prefix += self.prefix_append
        width, height = video.get_dimensions()
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(
            filename_prefix,
            self.output_dir,
            width,
            height
        )
        # Resolve local save directory and UI subfolder
        local_save_dir = full_output_folder
        ui_subfolder = subfolder
        if save_to_local:
            local_save_dir = os.path.join(full_output_folder, local_folder_path or "")
            try:
                os.makedirs(local_save_dir, exist_ok=True)
            except Exception:
                local_save_dir = full_output_folder
            ui_subfolder = os.path.join(subfolder, local_folder_path) if subfolder else local_folder_path

        results: list[FileLocator] = list()
        filenames: list[str] = []
        saved_metadata = None
        if not args.disable_metadata:
            metadata = {}
            if extra_pnginfo is not None:
                metadata.update(extra_pnginfo)
            if prompt is not None:
                metadata["prompt"] = prompt
            if len(metadata) > 0:
                saved_metadata = metadata
        # Use custom filename if provided, otherwise use default filename generation
        if custom_filename and custom_filename.strip():
            file = f"{custom_filename.strip()}.{Types.VideoContainer.get_extension(format)}"
        else:
            file = f"{filename}-{uuid4()}.{Types.VideoContainer.get_extension(format)}"
        out_path = os.path.join(local_save_dir, file)

        _notify("start", {"total": 1, "provider": cloud_provider if save_to_cloud else None})
        # Always render to disk first
        video.save_to(
            out_path,
            format=format,
            codec=codec,
            metadata=saved_metadata
        )

        cloud_results = []
        if save_to_local:
            results.append({
                "filename": file,
                "subfolder": ui_subfolder,
                "type": self.type
            })
            _notify("progress", {"where": "local", "current": 1, "total": 1, "filename": file})
        filenames.append(file)

        if save_to_cloud:
            try:
                with open(out_path, "rb") as f:
                    data = f.read()
                Uploader = get_uploader(cloud_provider)
                sent_bytes = {"n": 0}
                def _bytes_cb(info: dict):
                    delta = int(info.get("delta") or 0)
                    sent_bytes["n"] += delta
                    _notify("progress", {"where": "cloud", "bytes_done": sent_bytes["n"], "bytes_total": len(data), "filename": info.get("filename"), "provider": cloud_provider})
                def _progress_cb(info: dict):
                    _notify("progress", {"where": "cloud", "current": (info.get("index", 0) + 1), "total": 1, "filename": info.get("path"), "provider": cloud_provider})
                try:
                    cloud_results = Uploader.upload_many([{"filename": file, "content": data}], bucket_link, cloud_folder_path, cloud_api_key, _progress_cb, _bytes_cb)
                except TypeError:
                    cloud_results = Uploader.upload_many([{"filename": file, "content": data}], bucket_link, cloud_folder_path, cloud_api_key, _progress_cb)
            except Exception as e:
                _notify("error", {"message": str(e)})
            else:
                _notify("complete", {"count_local": len(results), "count_cloud": len(cloud_results), "provider": cloud_provider})
        else:
            _notify("complete", {"count_local": len(results), "count_cloud": 0, "provider": None})

        # If local is disabled, remove the temp file to keep workspace clean
        if not save_to_local:
            try:
                os.remove(out_path)
            except Exception:
                pass

        return { "ui": { "images": results, "animated": (True,) }, "result": (filenames,), "cloud": cloud_results }