from __future__ import annotations

import os
from io import BytesIO

import folder_paths
from comfy.comfy_types import IO, ComfyNodeABC
from comfy_api.latest import InputImpl
from server import PromptServer

from ..cloud import get_uploader


class LoadVideoExtended(ComfyNodeABC):
    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        files = folder_paths.filter_files_content_types(files, ["video"])
        return {
            "required": {
                "load_from_cloud": ("BOOLEAN", {"default": False, "socketless": True, "label_on": "Cloud", "label_off": "Local"}),
                "file_paths": ("STRING", {"multiline": True, "placeholder": "One filename per line"}),
                "local_file": (sorted(files), {"video_upload": True}),
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

    CATEGORY = "image/video"

    RETURN_TYPES = (IO.VIDEO,)
    FUNCTION = "load_video"
    def load_video(self, load_from_cloud: bool, file_paths: str, cloud_provider="AWS S3", bucket_link="", cloud_folder_path="", cloud_api_key="", local_file=None):
        def _notify(kind: str, payload: dict):
            try:
                PromptServer.instance.send_sync(
                    "comfyui.loadvideoextended.status",
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

        # For video input, we only return a single Video object. If multiple paths are provided, we load the first.
        name = paths[0]
        if load_from_cloud:
            Uploader = get_uploader(cloud_provider)
            try:
                raw = Uploader.download(name, bucket_link, cloud_folder_path, cloud_api_key)
            except Exception as e:
                _notify("error", {"message": str(e)})
                raise
            _notify("progress", {"where": "cloud", "current": 1, "total": 1, "filename": name, "provider": cloud_provider})
            vid = InputImpl.VideoFromFile(BytesIO(raw))
        else:
            video_path = folder_paths.get_annotated_filepath(name)
            vid = InputImpl.VideoFromFile(video_path)
            _notify("progress", {"where": "local", "current": 1, "total": 1, "filename": name})

        _notify("complete", {"count": 1, "provider": cloud_provider if load_from_cloud else None})
        return (vid,)

    @classmethod
    def IS_CHANGED(cls, load_from_cloud, file_paths, cloud_provider="AWS S3", bucket_link="", cloud_folder_path="", cloud_api_key="", local_file=None):
        if load_from_cloud:
            m = os.urandom(8)
            return m.hex()
        if local_file:
            video_path = folder_paths.get_annotated_filepath(local_file)
            return os.path.getmtime(video_path)
        if file_paths:
            name = [p.strip() for p in str(file_paths).splitlines() if p.strip()][0]
            video_path = folder_paths.get_annotated_filepath(name)
            return os.path.getmtime(video_path)
        return os.urandom(8).hex()

    @classmethod
    def VALIDATE_INPUTS(cls, load_from_cloud, file_paths, cloud_provider="AWS S3", bucket_link="", cloud_folder_path="", cloud_api_key="", local_file=None):
        if load_from_cloud:
            if not (cloud_provider and str(cloud_provider).strip()):
                return "Cloud: 'cloud_provider' is required."
            if not (bucket_link and bucket_link.strip()):
                return "Cloud: 'bucket_link' is required."
            if not (cloud_api_key and cloud_api_key.strip()):
                return "Cloud: 'cloud_api_key' is required."
            if not (file_paths and str(file_paths).strip()):
                return "Provide one or more file paths (one per line)."
        else:
            if not local_file and not (file_paths and str(file_paths).strip()):
                return "Select a local file or provide a path."
            name = local_file or [p.strip() for p in str(file_paths).splitlines() if p.strip()][0]
            if not folder_paths.exists_annotated_filepath(name):
                return "Invalid video file: {}".format(name)
        return True