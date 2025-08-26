from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

from io import BytesIO

import folder_paths
from comfy.cli_args import args

from .cloud import get_uploader


class SaveImageExtended:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save."}),
                "filename_prefix": ("STRING", {"default": "ComfyUI", "tooltip": "The prefix for the file to save. This may include formatting information such as %date:yyyy-MM-dd% or %Empty Latent Image.width% to include values from nodes."})
            },
            "optional": {
                # Cloud section (acts as a header toggle)
                "save_to_cloud": ("BOOLEAN", {"default": True, "socketless": True, "label_on": "Enabled", "label_off": "Disabled", "tooltip": "Section: Save to Cloud."}),
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
                    "S3-Compatible"
                ], {"default": "AWS S3", "tooltip": "Choose a cloud provider (required when cloud is enabled)."}),
                "bucket_link": ("STRING", {"default": "", "placeholder": "Bucket URL / Connection String*", "tooltip": "Provider target (format depends on provider). See Description for examples."}),
                "cloud_folder_path": ("STRING", {"default": "outputs", "placeholder": "Folder path in bucket (e.g. outputs)", "tooltip": "Path in the provider to store images (varies by provider)."}),
                "cloud_api_key": ("STRING", {"default": "", "placeholder": "Auth / API key*", "tooltip": "Credentials/token (format depends on provider). See Description for examples."}),

                # Local section
                "save_to_local": ("BOOLEAN", {"default": False, "socketless": True, "label_on": "Enabled", "label_off": "Disabled", "tooltip": "Section: Save to Local."}),
                "local_folder_path": ("STRING", {"default": "", "placeholder": "local/subfolder*", "tooltip": "Required when local save is enabled. Subfolder(s) under the ComfyUI output directory."}),
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images_extended"

    OUTPUT_NODE = True

    CATEGORY = "image"
    DESCRIPTION = (
        "Save Image Extended: Saves the input images to your chosen cloud provider or local ComfyUI output directory.\n"
        "\n"
        "Provider input formats:\n"
        "- AWS S3: bucket_link = 's3://<bucket>[/prefix]'; cloud_api_key = JSON {access_key, secret_key, region} or 'ACCESS:SECRET[:REGION]'.\n"
        "- S3-Compatible: bucket_link = 'https://<endpoint>/<bucket>[/prefix]'; cloud_api_key = same as S3.\n"
        "- Google Cloud Storage: bucket_link = 'gs://<bucket>[/prefix]' or '<bucket>[/prefix]'; cloud_api_key = service account JSON (string) or path to JSON (leave empty for ADC).\n"
        "- Azure Blob Storage: bucket_link = connection string OR 'https://<account>.blob.core.windows.net/<container>[/prefix]'; cloud_api_key = connection string or account key/SAS when using URL.\n"
        "- Backblaze B2: bucket_link = 'b2://<bucket>[/prefix]' or '<bucket>[/prefix]'; cloud_api_key = 'KEY_ID:APP_KEY'.\n"
        "- Google Drive: bucket_link = '/MyFolder/Sub' path OR 'drive://<folderId>/<optional/subpath>'; cloud_api_key = OAuth2 access token with Drive scope.\n"
        "- Dropbox: bucket_link = '/base/path' under Dropbox; cloud_api_key = access token.\n"
        "- OneDrive: bucket_link = '/base/path' under OneDrive root; cloud_api_key = OAuth2 access token.\n"
        "- FTP: bucket_link = 'ftp://user:pass@host[:port]/basepath'; cloud_api_key not used.\n"
        "- Supabase Storage: bucket_link = '<bucket_name>'; cloud_api_key = JSON {url, key} or 'url|key'.\n"
    )

    @classmethod
    def VALIDATE_INPUTS(s,
        images,
        filename_prefix="ComfyUI",
        save_to_cloud=True,
        cloud_provider="AWS S3",
        bucket_link="",
        cloud_folder_path="",
        cloud_api_key="",
        save_to_local=False,
        local_folder_path="",
        prompt=None,
        extra_pnginfo=None,
    ):
        if not save_to_cloud and not save_to_local:
            return "Enable at least one of 'Save to Cloud' or 'Save to Local'."
        if save_to_cloud:
            if not (cloud_provider and str(cloud_provider).strip()):
                return "Cloud: 'cloud_provider' is required."
            if not (bucket_link and bucket_link.strip()):
                return "Cloud: 'bucket_link' is required."
            if not (cloud_api_key and cloud_api_key.strip()):
                return "Cloud: 'cloud_api_key' is required."
        if save_to_local:
            if not (local_folder_path and local_folder_path.strip()):
                return "Local: 'local_folder_path' is required."
        return True

    def save_images_extended(self, 
        images, 
        filename_prefix="ComfyUI",
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
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        # Resolve local save directory and UI subfolder
        local_save_dir = full_output_folder
        ui_subfolder = subfolder
        if save_to_local and local_folder_path:
            local_save_dir = os.path.join(full_output_folder, local_folder_path)
            try:
                os.makedirs(local_save_dir, exist_ok=True)
            except Exception:
                local_save_dir = full_output_folder
            ui_subfolder = os.path.join(subfolder, local_folder_path) if subfolder else local_folder_path
        results = list()
        cloud_results = list()
        cloud_items = list()
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

            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            file = f"{filename_with_batch_num}_{counter:05}_.png"
            # Encode to PNG bytes once
            buffer = BytesIO()
            img.save(buffer, format="PNG", pnginfo=metadata, compress_level=self.compress_level)
            png_bytes = buffer.getvalue()

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

            if save_to_cloud:
                cloud_items.append({"filename": file, "content": png_bytes})
            counter += 1

        if save_to_cloud and cloud_items:
            try:
                Uploader = get_uploader(cloud_provider)
                if hasattr(Uploader, "upload_many"):
                    cloud_results = Uploader.upload_many(cloud_items, bucket_link, cloud_folder_path, cloud_api_key)
                else:
                    # Fallback to single uploads if batch not supported
                    for item in cloud_items:
                        info = Uploader.upload(item["content"], item["filename"], bucket_link, cloud_folder_path, cloud_api_key)
                        cloud_results.append(info)
            except Exception as e:
                print(f"[SaveImageExtended] Cloud batch upload failed: {e}")

        return { "ui": { "images": results }, "cloud": cloud_results }