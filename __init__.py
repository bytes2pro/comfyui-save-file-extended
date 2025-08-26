"""Top-level package for comfyui_save_file_extended."""

# Register client extension directory (root). JS in ./web/js, docs in ./web/docs
WEB_DIRECTORY = "./web"

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]

__authors__ = ["RUiNtheExtinct <deepkarma001@gmail.com>", "Prem Sai G <premsaig1605@gmail.com>"]
__author__ = ", ".join(__authors__)

__emails__ = ["deepkarma001@gmail.com", "premsaig1605@gmail.com"]
__email__ = ", ".join(__emails__)

__version__ = "0.0.1"

from .src.comfyui_save_file_extended.nodes import (NODE_CLASS_MAPPINGS,
                                                   NODE_DISPLAY_NAME_MAPPINGS)
