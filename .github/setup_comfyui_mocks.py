"""Setup minimal mocks for ComfyUI dependencies before node validation."""
import sys
from unittest.mock import MagicMock

# Mock torch and torchaudio (heavy dependencies not needed for validation)
mock_torch = MagicMock()
# Add common torch attributes that might be accessed
mock_torch.randn = MagicMock()
mock_torch.rand = MagicMock()
mock_torch.tensor = MagicMock()
mock_torch.Tensor = MagicMock()
mock_torch.int16 = MagicMock()
mock_torch.float = MagicMock()
sys.modules["torch"] = mock_torch

mock_torchaudio = MagicMock()
mock_torchaudio.functional = MagicMock()
mock_torchaudio.functional.resample = MagicMock()
sys.modules["torchaudio"] = mock_torchaudio

# Mock numpy
mock_numpy = MagicMock()
mock_numpy.ndarray = MagicMock()
sys.modules["numpy"] = mock_numpy
sys.modules["np"] = mock_numpy

# Mock PIL/Pillow
mock_pil = MagicMock()
mock_pil.Image = MagicMock()
mock_pil.PngImagePlugin = MagicMock()
mock_pil.PngImagePlugin.PngInfo = MagicMock()
sys.modules["PIL"] = mock_pil
sys.modules["PIL.Image"] = mock_pil.Image
sys.modules["PIL.PngImagePlugin"] = mock_pil.PngImagePlugin

# Mock av (PyAV)
mock_av = MagicMock()
mock_av.open = MagicMock()
mock_av.AudioFrame = MagicMock()
sys.modules["av"] = mock_av

# Mock cloud provider libraries (may not be installed in validation environment)
def _mock_module(name):
    """Create a mock module, handling nested dotted names."""
    if name in sys.modules:
        return sys.modules[name]
    
    parts = name.split(".")
    parent = None
    for i, part in enumerate(parts):
        full_name = ".".join(parts[:i+1])
        if full_name not in sys.modules:
            mock = MagicMock()
            sys.modules[full_name] = mock
            if parent:
                setattr(parent, part, mock)
            parent = mock
        else:
            parent = sys.modules[full_name]
    return sys.modules[name]

# Mock common cloud provider libraries
for module_name in [
    "boto3",
    "azure",
    "azure.storage",
    "azure.storage.blob",
    "google",
    "google.cloud",
    "google.cloud.storage",
    "google.oauth2",
    "google.oauth2.service_account",
    "b2sdk",
    "b2sdk.v2",
    "dropbox",
    "supabase",
    "requests",
]:
    _mock_module(module_name)

# Mock folder_paths
mock_folder_paths = MagicMock()
mock_folder_paths.get_output_directory.return_value = "/tmp/comfyui_output"
mock_folder_paths.get_save_image_path.return_value = (
    "/tmp/comfyui_output",
    "test_file",
    0,
    "",
    "test_prefix",
)
sys.modules["folder_paths"] = mock_folder_paths

# Mock server (PromptServer)
mock_prompt_server = MagicMock()
mock_prompt_server.instance = MagicMock()
mock_prompt_server.instance.send_sync = MagicMock()
sys.modules["server"] = mock_prompt_server

# Mock comfy.cli_args
mock_cli_args = MagicMock()
mock_cli_args.args = MagicMock()
mock_cli_args.args.disable_metadata = False
sys.modules["comfy.cli_args"] = mock_cli_args

# Mock comfy.comfy_types
class MockComfyNodeABC:
    """Mock base class for ComfyUI nodes."""
    pass

mock_comfy_types = MagicMock()
mock_comfy_types.FileLocator = dict
mock_comfy_types.ComfyNodeABC = MockComfyNodeABC
mock_comfy_types.IO = MagicMock()
sys.modules["comfy.comfy_types"] = mock_comfy_types

# Mock node_helpers
mock_node_helpers = MagicMock()
sys.modules["node_helpers"] = mock_node_helpers

# Mock comfy_api.latest
class MockComfyApiLatest:
    pass

mock_comfy_api = MagicMock()
mock_comfy_api.latest = MockComfyApiLatest()

# Mock comfy_api.latest types
mock_input = MagicMock()
mock_input_impl = MagicMock()

class MockVideoContainer:
    @staticmethod
    def as_input():
        return ["auto", "mp4", "webm"]
    
    @staticmethod
    def get_extension(format):
        format_map = {"mp4": "mp4", "webm": "webm", "mkv": "mkv", "auto": "mp4"}
        return format_map.get(format, "mp4")

mock_video_container = MockVideoContainer
mock_video_codec = MagicMock()
mock_video_codec.as_input.return_value = ["auto", "h264", "vp9"]

class MockTypes:
    VideoContainer = mock_video_container
    VideoCodec = mock_video_codec

mock_types = MockTypes()
mock_comfy_api.latest.Input = mock_input
mock_comfy_api.latest.InputImpl = mock_input_impl
mock_comfy_api.latest.Types = mock_types
sys.modules["comfy_api.latest"] = mock_comfy_api.latest

