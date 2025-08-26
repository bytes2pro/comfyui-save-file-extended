"""Top-level package for comfyui_save_file_extended."""

# Register client extension directory (root). JS in ./web/js, docs in ./web/docs
WEB_DIRECTORY = "./web"

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    'WEB_DIRECTORY',
]

__author__ = """RUiNtheExtinct"""
__email__ = "deepkarma001@gmail.com"
__version__ = "0.0.1"

from .src.comfyui_save_file_extended.nodes import (NODE_CLASS_MAPPINGS,
                                                   NODE_DISPLAY_NAME_MAPPINGS)
