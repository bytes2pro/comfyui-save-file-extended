"""Shared fixtures and mocks for all tests."""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import torch

# Add the project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock ComfyUI-specific imports before importing the nodes
# Create mock modules
mock_folder_paths = MagicMock()
mock_prompt_server = MagicMock()
mock_cli_args = MagicMock()
mock_comfy_types = MagicMock()
# Create a proper object for comfy_api.latest instead of MagicMock
class MockComfyApiLatest:
    pass
mock_comfy_api = MagicMock()
mock_comfy_api.latest = MockComfyApiLatest()
mock_node_helpers = MagicMock()

# Setup mocks
mock_folder_paths.get_output_directory.return_value = "/tmp/comfyui_output"
mock_folder_paths.get_save_image_path.return_value = (
    "/tmp/comfyui_output",
    "test_file",
    0,
    "",
    "test_prefix",
)

mock_cli_args.args = MagicMock()
mock_cli_args.args.disable_metadata = False

mock_prompt_server.instance = MagicMock()
mock_prompt_server.instance.send_sync = MagicMock()

# Inject mocks into sys.modules BEFORE any imports
sys.modules["folder_paths"] = mock_folder_paths
sys.modules["server"] = mock_prompt_server
sys.modules["comfy.cli_args"] = mock_cli_args
sys.modules["comfy.comfy_types"] = mock_comfy_types
# Note: We'll set comfy_api.latest after setting up the attributes
sys.modules["node_helpers"] = mock_node_helpers

# Mock comfy_api.latest types
mock_input = MagicMock()
mock_input_impl = MagicMock()

# Create a proper mock for VideoContainer with get_extension as a callable
# Use a regular class instead of MagicMock to avoid attribute access issues
class MockVideoContainer:
    @staticmethod
    def as_input():
        return ["auto", "mp4", "webm"]
    
    @staticmethod
    def get_extension(format):
        """Mock get_extension that returns extension based on format."""
        format_map = {"mp4": "mp4", "webm": "webm", "mkv": "mkv", "auto": "mp4"}
        return format_map.get(format, "mp4")

mock_video_container = MockVideoContainer  # Assign the class, not an instance

mock_video_codec = MagicMock()
mock_video_codec.as_input.return_value = ["auto", "h264", "vp9"]

# Create a simple object for Types instead of MagicMock to avoid attribute access issues
class MockTypes:
    VideoContainer = mock_video_container
    VideoCodec = mock_video_codec

mock_types = MockTypes()

mock_comfy_api.latest.Input = mock_input
mock_comfy_api.latest.InputImpl = mock_input_impl
mock_comfy_api.latest.Types = mock_types

# Now inject the latest module into sys.modules
sys.modules["comfy_api.latest"] = mock_comfy_api.latest

# Mock ComfyNodeABC as a simple base class
class MockComfyNodeABC:
    """Mock base class for ComfyUI nodes."""
    pass

mock_comfy_types.ComfyNodeABC = MockComfyNodeABC
mock_comfy_types.FileLocator = dict  # FileLocator is just a type alias for dict
mock_comfy_types.IO = MagicMock()

# Now import the nodes (after all mocks are set up)
from src.comfyui_save_file_extended.extended_nodes.save_audio_extended import (
    SaveAudioExtended)
from src.comfyui_save_file_extended.extended_nodes.save_image_extended import \
    SaveImageExtended
from src.comfyui_save_file_extended.extended_nodes.save_video_extended import (
    SaveVideoExtended, SaveWEBMExtended)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_audio_data():
    """Create mock audio data."""
    # Format: [B, C, T] = [batch, channels, time_samples]
    # For single batch: [1, 2, 16000] = 1 batch, 2 channels, 16000 samples
    waveform = torch.randn(1, 2, 16000)
    return {
        "waveform": waveform,
        "sample_rate": 44100,
    }


@pytest.fixture
def mock_image_data():
    """Create mock image data."""
    # Create a batch of 2 images, each 64x64 RGB
    images = torch.rand(2, 64, 64, 3)
    return images


@pytest.fixture
def mock_video_data():
    """Create mock video data."""
    mock_video = MagicMock()
    mock_video.get_dimensions.return_value = (1920, 1080)
    mock_video.save_to = MagicMock()
    return mock_video


@pytest.fixture
def save_audio_node():
    """Create SaveAudioExtended node instance."""
    with patch("src.comfyui_save_file_extended.extended_nodes.save_audio_extended.folder_paths", mock_folder_paths):
        node = SaveAudioExtended()
        node.output_dir = "/tmp/comfyui_output"
        return node


@pytest.fixture
def save_image_node():
    """Create SaveImageExtended node instance."""
    with patch("src.comfyui_save_file_extended.extended_nodes.save_image_extended.folder_paths", mock_folder_paths):
        node = SaveImageExtended()
        node.output_dir = "/tmp/comfyui_output"
        return node


@pytest.fixture
def save_webm_node():
    """Create SaveWEBMExtended node instance."""
    with patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.folder_paths", mock_folder_paths):
        node = SaveWEBMExtended()
        node.output_dir = "/tmp/comfyui_output"
        return node


@pytest.fixture
def save_video_node():
    """Create SaveVideoExtended node instance."""
    with patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.folder_paths", mock_folder_paths):
        node = SaveVideoExtended()
        node.output_dir = "/tmp/comfyui_output"
        return node
