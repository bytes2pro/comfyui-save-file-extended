from __future__ import annotations
import torch


import os
import sys
import json
import hashlib
import inspect
import traceback
import math
import time
import random
import logging

from PIL import Image, ImageOps, ImageSequence
from PIL.PngImagePlugin import PngInfo

import numpy as np
import safetensors.torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

import comfy.diffusers_load
import comfy.samplers
import comfy.sample
import comfy.sd
import comfy.utils
import comfy.controlnet
from comfy.comfy_types import IO, ComfyNodeABC, InputTypeDict, FileLocator
from comfy_api.internal import register_versions, ComfyAPIWithVersion
from comfy_api.version_list import supported_versions
from comfy_api.latest import io, ComfyExtension

import comfy.clip_vision

import comfy.model_management
from comfy.cli_args import args

import importlib

import folder_paths
import latent_preview
import node_helpers

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
                "save_to_cloud": ("BOOLEAN", {"default": True, "socketless": True, "label_on": "Enabled", "label_off": "Disabled", "tooltip": "Section: Save to Cloud (visual only)."}),
                "cloud_provider": ([
                    "AWS S3",
                    "Google Cloud Storage",
                    "Azure Blob Storage",
                    "Backblaze B2",
                    "Supabase Storage",
                    "S3-Compatible"
                ], {"default": "AWS S3", "tooltip": "Choose a cloud provider (visual only)."}),
                "bucket_link": ("STRING", {"default": "", "placeholder": "Bucket URL / Connection String", "tooltip": "Bucket URL or connection string (required when cloud is enabled)."}),
                "cloud_folder_path": ("STRING", {"default": "", "placeholder": "Folder path in bucket, e.g. outputs/", "tooltip": "Path inside the bucket to store images (required)."}),
                "cloud_api_key": ("STRING", {"default": "", "placeholder": "Auth / API key", "tooltip": "Auth/API key or credentials (required)."}),

                # Local section (visual only)
                "save_to_local": ("BOOLEAN", {"default": False, "socketless": True, "label_on": "Enabled", "label_off": "Disabled", "tooltip": "Section: Save to Local (visual only)."}),
                "local_folder_path": ("STRING", {"default": "", "placeholder": "/path/to/local/folder", "tooltip": "Local folder path (required when local is enabled)."}),
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images_extended"

    OUTPUT_NODE = True

    CATEGORY = "image"
    DESCRIPTION = "Save Image (Extended UI): adds visual controls for Cloud/Local destinations. Functionality is not yet implemented."

    def save_images_extended(self, images, filename_prefix="ComfyUI",
                             save_to_cloud=True,
                             cloud_provider="AWS S3",
                             bucket_link="",
                             cloud_folder_path="",
                             cloud_api_key="",
                             save_to_local=False,
                             local_folder_path="",
                             prompt=None, extra_pnginfo=None):
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        results = list()
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
            img.save(os.path.join(full_output_folder, file), pnginfo=metadata, compress_level=self.compress_level)
            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })
            counter += 1

        return { "ui": { "images": results } }

class PreviewImageExtended(SaveImageExtended):
    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append = "_temp_" + ''.join(random.choice("abcdefghijklmnopqrstupvxyz") for x in range(5))
        self.compress_level = 1

    @classmethod
    def INPUT_TYPES(s):
        return {"required":
                    {"images": ("IMAGE", ), },
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
                }
