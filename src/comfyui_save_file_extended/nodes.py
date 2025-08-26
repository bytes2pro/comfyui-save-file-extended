from .extended_nodes import *

# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "SaveImageExtended": SaveImageExtended,
    "LoadImageExtended": LoadImageExtended,
    "SaveVideoExtended": SaveVideoExtended,
    "SaveWEBMExtended": SaveWEBMExtended,
    "LoadVideoExtended": LoadVideoExtended,
    "SaveAudioExtended": SaveAudioExtended,
    "SaveAudioMP3Extended": SaveAudioMP3Extended,
    "SaveAudioOpusExtended": SaveAudioOpusExtended,
    "LoadAudioExtended": LoadAudioExtended,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageExtended": "Save Image Extended",
    "LoadImageExtended": "Load Image Extended",
    "SaveVideoExtended": "Save Video Extended",
    "SaveWEBMExtended": "Save WEBM Extended",
    "LoadVideoExtended": "Load Video Extended",
    "SaveAudioExtended": "Save Audio Extended",
    "SaveAudioMP3Extended": "Save Audio MP3 Extended",
    "SaveAudioOpusExtended": "Save Audio Opus Extended",
    "LoadAudioExtended": "Load Audio Extended",
}
