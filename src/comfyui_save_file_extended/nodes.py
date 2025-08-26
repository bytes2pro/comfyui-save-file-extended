from .load_image_extended import LoadImageExtended
from .save_image_extended import SaveImageExtended

# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "SaveImageExtended": SaveImageExtended,
    "LoadImageExtended": LoadImageExtended,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageExtended": "Save Image Extended",
    "LoadImageExtended": "Load Image Extended",
}
