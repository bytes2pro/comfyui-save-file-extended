from __future__ import annotations

import hashlib
import io
import os
import sys

import node_helpers
import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

import folder_paths

from .cloud import get_uploader


class LoadImageExtended:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "load_from_cloud": ("BOOLEAN", {"default": False, "socketless": True, "label_on": "Cloud", "label_off": "Local", "tooltip": "Choose source: cloud provider or local input directory."}),
                "file_paths": ("STRING", {"multiline": True, "placeholder": "One filename or key per line", "tooltip": "Files to load. For local: relative to the ComfyUI input directory or subfolders. For cloud: keys/paths relative to the chosen destination prefix."}),
            },
            "optional": {
                # Cloud configuration (used when load_from_cloud is True)
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
                ], {"default": "AWS S3", "tooltip": "Select the cloud provider. See Description for path formats."}),
                "bucket_link": ("STRING", {"default": "", "placeholder": "Bucket URL / Connection String", "tooltip": "Origin identifier. Examples: s3://bucket/prefix, gs://bucket, https://account.blob.core.windows.net/container, b2://bucket, drive://folderId, /Dropbox/Path, /OneDrive/Path, ftp://user:pass@host/basepath, or Supabase bucket name."}),
                "cloud_folder_path": ("STRING", {"default": "", "placeholder": "prefix/folder (optional)", "tooltip": "Optional folder/key prefix. Keys in file_paths will be resolved under this prefix."}),
                "cloud_api_key": ("STRING", {"default": "", "placeholder": "Auth / API key", "tooltip": "Credentials. Supports tokens and JSON. Drive/OneDrive support JSON with refresh_token for auto-refresh."}),
            },
        }

    CATEGORY = "image"
    DESCRIPTION = (
        "Load images from local input directory or from a cloud provider.\n"
        "- Local: file_paths are relative to the ComfyUI input directory (supports subfolders).\n"
        "- Cloud: file_paths are keys/filenames under the provided bucket/container/folder.\n"
        "\n"
        "Cloud provider examples:\n"
        "- S3 → bucket_link: s3://my-bucket/prefix\n"
        "- S3-Compatible → bucket_link: https://endpoint/bucket/prefix\n"
        "- GCS → bucket_link: gs://bucket/prefix or bucket/prefix\n"
        "- Azure Blob → bucket_link: connection string OR https://account.blob.core.windows.net/container/prefix\n"
        "- B2 → bucket_link: b2://bucket/prefix or bucket/prefix\n"
        "- Google Drive → bucket_link: /MyFolder/Sub OR drive://<folderId>/<optional/subpath>\n"
        "- Dropbox → bucket_link: /base/path\n"
        "- OneDrive → bucket_link: /base/path\n"
        "- FTP → bucket_link: ftp://user:pass@host[:port]/basepath\n"
        "- Supabase → bucket_link: <bucket_name>\n"
    )

    RETURN_TYPES = ("IMAGE", "MASK")
    FUNCTION = "load_images_extended"

    def _load_pil_from_bytes(self, raw: bytes) -> Image.Image:
        return Image.open(io.BytesIO(raw))

    def _tensor_and_mask_from_pil(self, img: Image.Image):
        output_images = []
        output_masks = []
        w, h = None, None
        excluded_formats = ['MPO']

        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)

            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            image = i.convert("RGB")

            if len(output_images) == 0:
                w = image.size[0]
                h = image.size[1]

            if image.size[0] != w or image.size[1] != h:
                continue

            image_np = np.array(image).astype(np.float32) / 255.0
            image_t = torch.from_numpy(image_np)[None,]
            if 'A' in i.getbands():
                mask_np = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask_t = 1. - torch.from_numpy(mask_np)
            elif i.mode == 'P' and 'transparency' in i.info:
                mask_np = np.array(i.convert('RGBA').getchannel('A')).astype(np.float32) / 255.0
                mask_t = 1. - torch.from_numpy(mask_np)
            else:
                mask_t = torch.zeros((64,64), dtype=torch.float32, device="cpu")
            output_images.append(image_t)
            output_masks.append(mask_t.unsqueeze(0))

        if len(output_images) > 1 and getattr(img, 'format', None) not in excluded_formats:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            output_image = output_images[0]
            output_mask = output_masks[0]
        return output_image, output_mask

    def load_images_extended(self, load_from_cloud: bool, file_paths: str, cloud_provider="AWS S3", bucket_link="", cloud_folder_path="", cloud_api_key=""):
        paths = [p.strip() for p in file_paths.splitlines() if p.strip()]
        if not paths:
            raise ValueError("Provide at least one file path")

        tensors = []
        masks = []

        if load_from_cloud:
            Uploader = get_uploader(cloud_provider)
            try:
                if hasattr(Uploader, "download_many"):
                    results = Uploader.download_many(paths, bucket_link, cloud_folder_path, cloud_api_key)
                else:
                    results = [{"filename": name, "content": Uploader.download(name, bucket_link, cloud_folder_path, cloud_api_key)} for name in paths]
            except Exception as e:
                raise RuntimeError(f"Cloud download failed: {e}")

            for res in results:
                pil = self._load_pil_from_bytes(res["content"]) 
                img_t, mask_t = self._tensor_and_mask_from_pil(pil)
                tensors.append(img_t)
                masks.append(mask_t)
        else:
            input_dir = folder_paths.get_input_directory()
            for rel in paths:
                image_path = os.path.join(input_dir, rel)
                if not os.path.isfile(image_path):
                    raise FileNotFoundError(image_path)
                img = node_helpers.pillow(Image.open, image_path)
                img_t, mask_t = self._tensor_and_mask_from_pil(img)
                tensors.append(img_t)
                masks.append(mask_t)

        # Attempt to batch concatenate if shapes match
        def can_stack(ts):
            base = ts[0].shape
            return all(t.shape[1:] == base[1:] for t in ts)

        if len(tensors) > 1 and can_stack(tensors) and can_stack(masks):
            out_img = torch.cat(tensors, dim=0)
            out_mask = torch.cat(masks, dim=0)
        else:
            out_img = tensors[0]
            out_mask = masks[0]

        return (out_img, out_mask)

    @classmethod
    def IS_CHANGED(s, load_from_cloud, file_paths, cloud_provider="AWS S3", bucket_link="", cloud_folder_path="", cloud_api_key=""):
        # Hash input arguments to trigger reload when they change
        m = hashlib.sha256()
        for part in [str(load_from_cloud), str(file_paths), str(cloud_provider), str(bucket_link), str(cloud_folder_path)]:
            m.update(part.encode("utf-8"))
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(s, load_from_cloud, file_paths, cloud_provider="AWS S3", bucket_link="", cloud_folder_path="", cloud_api_key=""):
        if not file_paths or not file_paths.strip():
            return "Provide one or more file paths (one per line)."
        if load_from_cloud:
            if not (cloud_provider and str(cloud_provider).strip()):
                return "Cloud: 'cloud_provider' is required."
            if not (bucket_link and bucket_link.strip()):
                return "Cloud: 'bucket_link' is required."
            if not (cloud_api_key and cloud_api_key.strip()):
                return "Cloud: 'cloud_api_key' is required."
        return True