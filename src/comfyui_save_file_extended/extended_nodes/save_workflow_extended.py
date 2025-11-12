from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

from inspect import cleandoc

import folder_paths
from server import PromptServer

from ..cloud import get_uploader
from ..utils import sanitize_filename


class SaveWorkflowExtended:
    """
    Save workflow JSON files locally and/or upload to a cloud provider.

    How it works
    ------------
    - Local: Saves workflow JSON files under the ComfyUI output directory (only if 'Save to Local' is enabled).
    - Cloud: Uploads workflow JSON files to cloud storage (only if 'Save to Cloud' is enabled).
    - Result: Returns the saved filename and cloud upload details.

    The workflow JSON includes:
    - The prompt (workflow structure with nodes and connections)
    - Extra data (UI positions, metadata, etc.)

    Cloud provider examples
    -----------------------
    - AWS S3 → bucket_link: s3://my-bucket/prefix | cloud_api_key: JSON {access_key, secret_key, region} or 'ACCESS:SECRET[:REGION]'.
    - S3-Compatible → bucket_link: https://endpoint.example.com/my-bucket/prefix | cloud_api_key: same as S3.
    - Google Cloud Storage → bucket_link: gs://bucket/prefix or bucket/prefix | cloud_api_key: service-account JSON string or path (empty uses ADC).
    - Azure Blob → bucket_link: connection string OR https://account.blob.core.windows.net/container/prefix | cloud_api_key: connection string or account key/SAS when using URL.
    - Backblaze B2 → bucket_link: b2://bucket/prefix or bucket/prefix | cloud_api_key: KEY_ID:APP_KEY.
    - Google Drive → bucket_link: /MyFolder/Sub OR drive://<folderId>/<optional/subpath> | cloud_api_key: OAuth2 access token.
    - Dropbox → bucket_link: /base/path | cloud_api_key: access token.
    - OneDrive → bucket_link: /base/path | cloud_api_key: OAuth2 access token.
    - FTP → bucket_link: ftp://user:pass@host[:port]/basepath | cloud_api_key: not used.
    - Supabase → bucket_link: <bucket_name> | cloud_api_key: JSON {url, key} or 'url|key'.
    - UploadThing → bucket_link: (leave blank) | cloud_api_key: UploadThing secret key (sk_...). Returns utfs.io URLs.

    Token refresh (optional)
    ------------------------
    - Google Drive cloud_api_key JSON: {client_id, client_secret, refresh_token} (optional access_token).
    - OneDrive cloud_api_key JSON: {client_id, client_secret, refresh_token, tenant='common'|'consumers'|'organizations', redirect_uri?}.
    When provided, a fresh access token is obtained automatically before uploading.
    """
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "filename_prefix": ("STRING", {"default": "workflows/ComfyUI", "tooltip": "Filename prefix. Supports tokens like %date:yyyy-MM-dd% and node field tokens."})
            },
            "optional": {
                "filename": ("STRING", {"default": "", "placeholder": "Filename (optional)", "tooltip": "Exact filename to use. If provided, this will be used directly. If empty, uses UUID-based filename generation. Include file extension (.json)."}),
                "custom_filename": ("STRING", {"default": "", "placeholder": "Custom filename (optional)", "tooltip": "Custom filename for saved workflow. If empty, uses the default filename generation with prefix and UUID. Do not include file extension."}),
                # Cloud section (acts as a header toggle)
                "save_to_cloud": ("BOOLEAN", {"default": True, "socketless": True, "label_on": "Enabled", "label_off": "Disabled", "tooltip": "Enable uploading to a cloud provider. Configure provider, destination, and credentials below."}),
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
                ], {"default": "AWS S3", "tooltip": "Select the cloud provider. See Description for exact formats."}),
                "bucket_link": ("STRING", {"default": "", "placeholder": "Bucket URL / Connection String*", "tooltip": "Destination identifier (varies by provider). Examples: s3://bucket/prefix, gs://bucket, https://account.blob.core.windows.net/container, b2://bucket, drive://folderId, /Dropbox/Path, /OneDrive/Path, ftp://user:pass@host/basepath, or Supabase bucket name. See Description. For UploadThing, leave blank."}),
                "cloud_folder_path": ("STRING", {"default": "workflows", "placeholder": "Folder path in bucket (e.g. workflows)", "tooltip": "Folder/key prefix under the destination. Created if missing (where applicable)."}),
                "cloud_api_key": ("STRING", {"default": "", "placeholder": "Auth / API key*", "tooltip": "Credentials. Supports tokens and JSON. For Drive/OneDrive, JSON with refresh_token will auto-refresh the access token. For UploadThing, use your secret key (sk_...). See Description."}),

                # Local section
                "save_to_local": ("BOOLEAN", {"default": False, "socketless": True, "label_on": "Enabled", "label_off": "Disabled", "tooltip": "Write workflow JSON files to the ComfyUI output directory (in addition to cloud when enabled)."}),
                "local_folder_path": ("STRING", {"default": "", "placeholder": "local/subfolder*", "tooltip": "When local save is enabled, writes under this subfolder of the ComfyUI output directory. Created if missing."}),
                "append_timestamp": ("BOOLEAN", {"default": True, "socketless": True, "label_on": "Enabled", "label_off": "Disabled", "tooltip": "Append timestamp to filename to prevent overwriting. If disabled and filename is provided, will overwrite existing files."}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filename",)
    FUNCTION = "save_workflow_extended"

    OUTPUT_NODE = True

    CATEGORY = "workflow"
    DESCRIPTION = cleandoc(__doc__)

    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        save_to_cloud = kwargs.get("save_to_cloud", True)
        save_to_local = kwargs.get("save_to_local", False)
        cloud_provider = kwargs.get("cloud_provider", "AWS S3")
        bucket_link = kwargs.get("bucket_link", "")
        cloud_api_key = kwargs.get("cloud_api_key", "")
        if not save_to_cloud and not save_to_local:
            return "Enable at least one of 'Save to Cloud' or 'Save to Local'."
        if save_to_cloud:
            if not (cloud_provider and str(cloud_provider).strip()):
                return "Cloud: 'cloud_provider' is required."
            provider_lower = str(cloud_provider).lower()
            # UploadThing doesn't require bucket_link (should be left blank)
            if provider_lower != "uploadthing" and not (bucket_link and bucket_link.strip()):
                return "Cloud: 'bucket_link' is required."
            # FTP doesn't require cloud_api_key (credentials are in bucket_link URL)
            if provider_lower != "ftp" and not (cloud_api_key and cloud_api_key.strip()):
                return "Cloud: 'cloud_api_key' is required."
        return True

    def save_workflow_extended(self,
        filename_prefix="workflows/ComfyUI",
        filename="",
        custom_filename="",
        save_to_cloud=True,
        cloud_provider="AWS S3",
        bucket_link="",
        cloud_folder_path="workflows",
        cloud_api_key="",
        save_to_local=False,
        local_folder_path="",
        append_timestamp=True,
        prompt=None,
        extra_pnginfo=None
    ):
        def _toast(kind: str, title: str, message: str):
            # Try several common ComfyUI notification channels; ignore failures
            try:
                PromptServer.instance.send_sync(
                    "display_notification",
                    {"kind": kind, "title": title, "message": message},
                )
            except Exception:
                pass
            try:
                PromptServer.instance.send_sync(
                    "notification",
                    {"kind": kind, "title": title, "message": message},
                )
            except Exception:
                pass
            try:
                PromptServer.instance.send_sync(
                    "display_component",
                    {"component": "Toast", "props": {"kind": kind, "title": title, "message": message}},
                )
            except Exception:
                pass

        filename_prefix += self.prefix_append

        # Get save path (using get_save_image_path for consistency, though we're saving JSON)
        full_output_folder, base_filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir)

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

        # Construct workflow JSON
        workflow_data = {}
        if prompt is not None:
            workflow_data["prompt"] = prompt
        if extra_pnginfo is not None:
            workflow_data["extra"] = extra_pnginfo
        else:
            workflow_data["extra"] = {}

        # Convert to JSON bytes
        workflow_json_str = json.dumps(workflow_data, indent=2)
        workflow_json_bytes = workflow_json_str.encode('utf-8')

        # Determine filename
        sanitized_filename = sanitize_filename(filename) if filename else None

        # Generate timestamp suffix if append_timestamp is enabled
        timestamp_suffix = ""
        if append_timestamp:
            timestamp_suffix = f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if sanitized_filename:
            # Use sanitized basename for safe filename handling
            name, ext = os.path.splitext(sanitized_filename)
            if not ext:
                ext = ".json"
            if append_timestamp:
                file = f"{name}{timestamp_suffix}{ext}"
            else:
                file = f"{name}{ext}"
        elif custom_filename and custom_filename.strip():
            if append_timestamp:
                file = f"{custom_filename.strip()}{timestamp_suffix}.json"
            else:
                file = f"{custom_filename.strip()}.json"
        else:
            # Default: always use UUID (unique each time)
            file = f"{base_filename}-{uuid4()}.json"

        results = []
        cloud_results = []

        try:
            PromptServer.instance.send_sync(
                "comfyui.saveworkflowextended.status",
                {"phase": "start", "total": 1, "provider": cloud_provider if save_to_cloud else None}
            )
        except Exception:
            pass

        if save_to_local:
            print(f"Saving workflow locally to {local_save_dir}")
            try:
                file_path = os.path.join(local_save_dir, file)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(workflow_json_str)
                results.append({
                    "filename": file,
                    "subfolder": ui_subfolder,
                    "type": self.type
                })
                try:
                    PromptServer.instance.send_sync(
                        "comfyui.saveworkflowextended.status",
                        {"phase": "progress", "where": "local", "current": 1, "total": 1, "filename": file}
                    )
                except Exception:
                    pass
            except Exception as e:
                print(f"[SaveWorkflowExtended] Failed to save locally: {e}")
                try:
                    PromptServer.instance.send_sync(
                        "comfyui.saveworkflowextended.status",
                        {"phase": "error", "message": str(e)}
                    )
                except Exception:
                    pass

        if save_to_cloud:
            print(f"Uploading workflow to cloud provider: {cloud_provider}")
            try:
                Uploader = get_uploader(cloud_provider)
                total_bytes = len(workflow_json_bytes)
                sent_bytes = {"n": 0}

                def _bytes_cb(info: dict):
                    delta = int(info.get("delta") or 0)
                    sent_bytes["n"] += delta
                    try:
                        PromptServer.instance.send_sync(
                            "comfyui.saveworkflowextended.status",
                            {"phase": "progress", "where": "cloud", "bytes_done": sent_bytes["n"], "bytes_total": total_bytes, "filename": info.get("filename"), "provider": cloud_provider}
                        )
                    except Exception:
                        pass

                def _progress_cb(info: dict):
                    try:
                        PromptServer.instance.send_sync(
                            "comfyui.saveworkflowextended.status",
                            {"phase": "progress", "where": "cloud", "current": 1, "total": 1, "filename": info.get("path"), "provider": cloud_provider}
                        )
                    except Exception:
                        pass

                cloud_items = [{"filename": file, "content": workflow_json_bytes}]

                if hasattr(Uploader, "upload_many"):
                    try:
                        cloud_results = Uploader.upload_many(cloud_items, bucket_link, cloud_folder_path, cloud_api_key, _progress_cb, _bytes_cb)
                    except TypeError:
                        cloud_results = Uploader.upload_many(cloud_items, bucket_link, cloud_folder_path, cloud_api_key, _progress_cb)
                else:
                    # Fallback to single upload if batch not supported
                    info = Uploader.upload(workflow_json_bytes, file, bucket_link, cloud_folder_path, cloud_api_key)
                    cloud_results = [info]
                    try:
                        PromptServer.instance.send_sync(
                            "comfyui.saveworkflowextended.status",
                            {"phase": "progress", "where": "cloud", "current": 1, "total": 1, "filename": info.get("path"), "provider": cloud_provider}
                        )
                    except Exception:
                        pass
            except Exception as e:
                print(f"[SaveWorkflowExtended] Cloud upload failed: {e}")
                try:
                    PromptServer.instance.send_sync(
                        "comfyui.saveworkflowextended.status",
                        {"phase": "error", "message": str(e)}
                    )
                except Exception:
                    pass
            else:
                try:
                    PromptServer.instance.send_sync(
                        "comfyui.saveworkflowextended.status",
                        {"phase": "complete", "count_local": len(results), "count_cloud": len(cloud_results), "provider": cloud_provider}
                    )
                except Exception:
                    pass

        # If we didn't perform a cloud upload (local-only or no items), still send a complete status
        if not save_to_cloud:
            try:
                PromptServer.instance.send_sync(
                    "comfyui.saveworkflowextended.status",
                    {"phase": "complete", "count_local": len(results), "count_cloud": 0, "provider": None}
                )
            except Exception:
                pass

        return {"ui": {"text": results}, "result": (file,), "cloud": cloud_results}

