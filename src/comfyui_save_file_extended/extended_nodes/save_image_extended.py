from __future__ import annotations

import json
import os
import sys
from uuid import uuid4

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

from inspect import cleandoc
from io import BytesIO

import folder_paths
from comfy.cli_args import args
from server import PromptServer

from ..cloud import get_uploader
from ..utils import sanitize_filename


class SaveImageExtended:
    """
    Save images locally and/or upload to a cloud provider.

    How it works
    ------------
    - Local: Saves PNG files under the ComfyUI output directory (only if 'Save to Local' is enabled).
    - Cloud: Uploads all images in one batch per run (only if 'Save to Cloud' is enabled).
    - Result: UI shows local files; cloud upload details are returned in the node output under 'cloud'.

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
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "Image tensor batch to save."}),
                "filename_prefix": ("STRING", {"default": "ComfyUI", "tooltip": "Filename prefix. Supports tokens like %date:yyyy-MM-dd% and node field tokens (e.g. %Empty Latent Image.width%)."})
            },
            "optional": {
                "filename": ("STRING", {"default": "", "placeholder": "Filename (optional)", "tooltip": "Exact filename to use. If provided, this will be used directly. If empty, uses UUID-based filename generation. Include file extension."}),
                "custom_filename": ("STRING", {"default": "", "placeholder": "Custom filename (optional)", "tooltip": "Custom filename for saved images. If empty, uses the default filename generation with prefix and UUID. Do not include file extension."}),
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
                "cloud_folder_path": ("STRING", {"default": "outputs", "placeholder": "Folder path in bucket (e.g. outputs)", "tooltip": "Folder/key prefix under the destination. Created if missing (where applicable)."}),
                "cloud_api_key": ("STRING", {"default": "", "placeholder": "Auth / API key*", "tooltip": "Credentials. Supports tokens and JSON. For Drive/OneDrive, JSON with refresh_token will auto-refresh the access token. For UploadThing, use your secret key (sk_...). See Description."}),

                # Local section
                "save_to_local": ("BOOLEAN", {"default": False, "socketless": True, "label_on": "Enabled", "label_off": "Disabled", "tooltip": "Write PNGs to the ComfyUI output directory (in addition to cloud when enabled)."}),
                "local_folder_path": ("STRING", {"default": "", "placeholder": "local/subfolder*", "tooltip": "When local save is enabled, writes under this subfolder of the ComfyUI output directory. Created if missing."}),
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filenames",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "save_images_extended"

    OUTPUT_NODE = True

    CATEGORY = "image"
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
            if not (bucket_link and bucket_link.strip()):
                return "Cloud: 'bucket_link' is required."
            if not (cloud_api_key and cloud_api_key.strip()):
                return "Cloud: 'cloud_api_key' is required."
        return True

    def save_images_extended(self,
        images,
        filename_prefix="ComfyUI",
        filename="",
        custom_filename="",
        save_to_cloud=True,
        cloud_provider="AWS S3",
        bucket_link="",
        cloud_folder_path="outputs",
        cloud_api_key="",
        save_to_local=False,
        local_folder_path="",
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
        full_output_folder, base_filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
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
        results = list()
        filenames = list()
        cloud_results = list()
        cloud_items = list()
        total = len(images)
        try:
            PromptServer.instance.send_sync(
                "comfyui.saveimageextended.status",
                {"phase": "start", "total": total, "provider": cloud_provider if save_to_cloud else None}
            )
        except Exception:
            pass
        if save_to_local:
            print(f"Saving images locally to {local_save_dir}")
        if save_to_cloud:
            print(f"Uploading images to cloud provider: {cloud_provider}")
        for (batch_number, image) in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            # Use filename if provided, otherwise use custom_filename or default UUID generation
            # Sanitize inputs to prevent path traversal attacks
            sanitized_filename = sanitize_filename(filename) if filename else None
            sanitized_custom_filename = sanitize_filename(custom_filename) if custom_filename else None

            if sanitized_filename:
                # Use sanitized basename for safe filename handling
                if len(images) > 1:
                    # For batch, append batch number before extension
                    name, ext = os.path.splitext(sanitized_filename)
                    if not ext:
                        ext = ".png"
                    file = f"{name}_{batch_number:03d}{ext}"
                else:
                    name, ext = os.path.splitext(sanitized_filename)
                    if not ext:
                        ext = ".png"
                    file = f"{name}{ext}"
            elif sanitized_custom_filename:
                if len(images) > 1:
                    file = f"{sanitized_custom_filename}_{batch_number:03d}.png"
                else:
                    file = f"{sanitized_custom_filename}.png"
            else:
                filename_with_batch_num = base_filename.replace("%batch_num%", str(batch_number))
                file = f"{filename_with_batch_num}-{uuid4()}.png"
            # Encode to PNG bytes once
            buffer = BytesIO()
            img.save(buffer, format="PNG", pnginfo=metadata, compress_level=self.compress_level)
            png_bytes = buffer.getvalue()
            filenames.append(file)

            if save_to_local:
                try:
                    with open(os.path.join(local_save_dir, file), "wb") as f:
                        f.write(png_bytes)
                    results.append({
                        "filename": file,
                        "subfolder": ui_subfolder,
                        "type": self.type
                    })
                except Exception as e:
                    print(f"[SaveImageExtended] Failed to save locally: {e}")
                    try:
                        PromptServer.instance.send_sync(
                            "comfyui.saveimageextended.status",
                            {"phase": "error", "message": str(e)}
                        )
                    except Exception:
                        pass
                else:
                    try:
                        PromptServer.instance.send_sync(
                            "comfyui.saveimageextended.status",
                            {"phase": "progress", "where": "local", "current": counter, "total": total, "filename": file}
                        )
                    except Exception:
                        pass

            if save_to_cloud:
                cloud_items.append({"filename": file, "content": png_bytes})
            counter += 1

        if save_to_cloud and cloud_items:
            try:
                Uploader = get_uploader(cloud_provider)
                total_bytes = sum(len(it["content"]) for it in cloud_items)
                sent_bytes = {"n": 0}
                def _bytes_cb(info: dict):
                    delta = int(info.get("delta") or 0)
                    sent_bytes["n"] += delta
                    try:
                        PromptServer.instance.send_sync(
                            "comfyui.saveimageextended.status",
                            {"phase": "progress", "where": "cloud", "bytes_done": sent_bytes["n"], "bytes_total": total_bytes, "filename": info.get("filename"), "provider": cloud_provider}
                        )
                    except Exception:
                        pass
                if hasattr(Uploader, "upload_many"):
                    def _progress_cb(info: dict):
                        try:
                            PromptServer.instance.send_sync(
                                "comfyui.saveimageextended.status",
                                {"phase": "progress", "where": "cloud", "current": (info.get("index", 0) + 1), "total": len(cloud_items), "filename": info.get("path"), "provider": cloud_provider}
                            )
                        except Exception:
                            pass
                    try:
                        cloud_results = Uploader.upload_many(cloud_items, bucket_link, cloud_folder_path, cloud_api_key, _progress_cb, _bytes_cb)
                    except TypeError:
                        cloud_results = Uploader.upload_many(cloud_items, bucket_link, cloud_folder_path, cloud_api_key, _progress_cb)
                else:
                    # Fallback to single uploads if batch not supported
                    sent = 0
                    for item in cloud_items:
                        info = Uploader.upload(item["content"], item["filename"], bucket_link, cloud_folder_path, cloud_api_key)
                        cloud_results.append(info)
                        sent += 1
                        try:
                            PromptServer.instance.send_sync(
                                "comfyui.saveimageextended.status",
                                {"phase": "progress", "where": "cloud", "current": sent, "total": len(cloud_items), "filename": info.get("path"), "provider": cloud_provider}
                            )
                        except Exception:
                            pass
            except Exception as e:
                print(f"[SaveImageExtended] Cloud batch upload failed: {e}")
                try:
                    PromptServer.instance.send_sync(
                        "comfyui.saveimageextended.status",
                        {"phase": "error", "message": str(e)}
                    )
                except Exception:
                    pass
            else:
                try:
                    PromptServer.instance.send_sync(
                        "comfyui.saveimageextended.status",
                        {"phase": "complete", "count_local": len(results), "count_cloud": len(cloud_results), "provider": cloud_provider}
                    )
                except Exception:
                    pass

        # If we didn't perform a cloud upload (local-only or no items), still send a complete status
        if not save_to_cloud or not cloud_items:
            try:
                PromptServer.instance.send_sync(
                    "comfyui.saveimageextended.status",
                    {"phase": "complete", "count_local": len(results), "count_cloud": 0, "provider": None}
                )
            except Exception:
                pass

        return { "ui": { "images": results }, "result": (filenames,), "cloud": cloud_results }
