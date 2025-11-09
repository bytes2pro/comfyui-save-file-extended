"""Tests for SaveAudioExtended, SaveAudioMP3Extended, and SaveAudioOpusExtended nodes."""

from unittest.mock import MagicMock, patch

# Import classes - conftest sets up mocks before these imports
from src.comfyui_save_file_extended.extended_nodes.save_audio_extended import (
    SaveAudioExtended, SaveAudioMP3Extended, SaveAudioOpusExtended)

from .conftest import mock_folder_paths


class TestSaveAudioExtended:
    """Test SaveAudioExtended node."""

    def test_filename_parameter_single_file(self, save_audio_node, mock_audio_data, temp_dir):
        """Test that filename parameter is used when provided for single file."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_audio_extended.get_uploader") as mock_get_uploader, \
             patch.object(save_audio_node, "_encode_one", return_value=b"fake_audio_data"):

            result = save_audio_node.save_audio(
                mock_audio_data,
                filename_prefix="test",
                format="flac",
                filename="my_audio.flac",
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that the filename was used
            assert "my_audio.flac" in result["result"][0]
            assert len(result["result"][0]) == 1
            assert result["result"][0][0] == "my_audio.flac"

    def test_filename_parameter_without_extension(self, save_audio_node, mock_audio_data, temp_dir):
        """Test that extension is auto-appended when filename lacks extension."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_audio_extended.get_uploader"), \
             patch.object(save_audio_node, "_encode_one", return_value=b"fake_audio_data"):

            result = save_audio_node.save_audio(
                mock_audio_data,
                filename_prefix="test",
                format="mp3",
                filename="my_audio",  # No extension
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that extension was appended
            assert "my_audio.mp3" in result["result"][0]
            assert result["result"][0][0] == "my_audio.mp3"

    def test_filename_parameter_batch(self, save_audio_node, mock_audio_data, temp_dir):
        """Test that filename parameter works correctly for batch processing."""
        import torch

        # Create batch of 3 audio files
        # Format: [B, C, T] = [3, 2, 16000] = 3 batches, 2 channels, 16000 samples
        batch_waveform = torch.randn(3, 2, 16000)
        mock_audio_data["waveform"] = batch_waveform

        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_audio_extended.get_uploader"), \
             patch.object(save_audio_node, "_encode_one", return_value=b"fake_audio_data"):

            result = save_audio_node.save_audio(
                mock_audio_data,
                filename_prefix="test",
                format="wav",
                filename="batch_audio.wav",
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that batch numbers were appended
            filenames = result["result"][0]
            assert len(filenames) == 3
            assert filenames[0] == "batch_audio_000.wav"
            assert filenames[1] == "batch_audio_001.wav"
            assert filenames[2] == "batch_audio_002.wav"

    def test_custom_filename_parameter(self, save_audio_node, mock_audio_data, temp_dir):
        """Test that custom_filename parameter works when filename is empty."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_audio_extended.get_uploader"), \
             patch.object(save_audio_node, "_encode_one", return_value=b"fake_audio_data"):

            result = save_audio_node.save_audio(
                mock_audio_data,
                filename_prefix="test",
                format="opus",
                filename="",  # Empty filename
                custom_filename="custom_audio",
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that custom_filename was used with extension
            assert "custom_audio.opus" in result["result"][0]
            assert result["result"][0][0] == "custom_audio.opus"

    def test_uuid_fallback(self, save_audio_node, mock_audio_data, temp_dir):
        """Test that UUID-based filename is used when both filename and custom_filename are empty."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_audio_extended.get_uploader"), \
             patch.object(save_audio_node, "_encode_one", return_value=b"fake_audio_data"):

            result = save_audio_node.save_audio(
                mock_audio_data,
                filename_prefix="test",
                format="flac",
                filename="",  # Empty
                custom_filename="",  # Empty
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that UUID-based filename was generated
            filenames = result["result"][0]
            assert len(filenames) == 1
            assert filenames[0].startswith("test_file-")
            assert filenames[0].endswith(".flac")
            # Check UUID format (36 chars + .flac)
            assert len(filenames[0]) > 40

    def test_filename_priority(self, save_audio_node, mock_audio_data, temp_dir):
        """Test that filename takes priority over custom_filename."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_audio_extended.get_uploader"), \
             patch.object(save_audio_node, "_encode_one", return_value=b"fake_audio_data"):

            result = save_audio_node.save_audio(
                mock_audio_data,
                filename_prefix="test",
                format="mp3",
                filename="priority.mp3",  # Should be used
                custom_filename="ignored",  # Should be ignored
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that filename was used, not custom_filename
            assert "priority.mp3" in result["result"][0]
            assert result["result"][0][0] == "priority.mp3"
            assert "ignored" not in result["result"][0][0]

    def test_whitespace_only_filename(self, save_audio_node, mock_audio_data, temp_dir):
        """Test that whitespace-only filename is treated as empty."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_audio_extended.get_uploader"), \
             patch.object(save_audio_node, "_encode_one", return_value=b"fake_audio_data"):

            result = save_audio_node.save_audio(
                mock_audio_data,
                filename_prefix="test",
                format="flac",
                filename="   ",  # Whitespace only
                custom_filename="fallback",
                save_to_local=True,
                save_to_cloud=False,
            )

            # Should fall back to custom_filename
            assert "fallback.flac" in result["result"][0]
            assert result["result"][0][0] == "fallback.flac"

    def test_local_folder_path(self, save_audio_node, mock_audio_data, temp_dir):
        """Test that local_folder_path creates subdirectory correctly."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True) as mock_makedirs, \
             patch("src.comfyui_save_file_extended.extended_nodes.save_audio_extended.get_uploader"), \
             patch.object(save_audio_node, "_encode_one", return_value=b"fake_audio_data"):

            result = save_audio_node.save_audio(
                mock_audio_data,
                filename_prefix="test",
                format="flac",
                filename="test.flac",
                save_to_local=True,
                save_to_cloud=False,
                local_folder_path="audio/subfolder",
            )

            # Verify makedirs was called with subfolder path
            assert mock_makedirs.called
            # Check that subfolder path was used
            call_args = [str(call) for call in mock_makedirs.call_args_list]
            assert any("audio/subfolder" in str(arg) for arg in call_args)

    def test_cloud_upload_enabled(self, save_audio_node, mock_audio_data, temp_dir):
        """Test that cloud upload is attempted when enabled."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        mock_uploader = MagicMock()
        mock_uploader.upload_many = MagicMock(return_value=[{"url": "http://example.com/file.flac"}])

        with patch("builtins.open", create=True), \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_audio_extended.get_uploader", return_value=mock_uploader), \
             patch.object(save_audio_node, "_encode_one", return_value=b"fake_audio_data"):

            result = save_audio_node.save_audio(
                mock_audio_data,
                filename_prefix="test",
                format="flac",
                filename="test.flac",
                save_to_local=True,
                save_to_cloud=True,
                cloud_provider="AWS S3",
                bucket_link="s3://test-bucket",
                cloud_api_key="test-key",
            )

            # Verify uploader was called
            assert mock_uploader.upload_many.called
            assert "cloud" in result
            assert len(result["cloud"]) > 0

    def test_metadata_included(self, save_audio_node, mock_audio_data, temp_dir):
        """Test that metadata (prompt, extra_pnginfo) is included in saved files."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        test_prompt = {"test": "prompt"}
        test_extra = {"test_key": "test_value"}

        with patch("builtins.open", create=True), \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_audio_extended.get_uploader"), \
             patch.object(save_audio_node, "_encode_one", return_value=b"fake_audio_data") as mock_encode:

            save_audio_node.save_audio(
                mock_audio_data,
                filename_prefix="test",
                format="flac",
                filename="test.flac",
                save_to_local=True,
                save_to_cloud=False,
                prompt=test_prompt,
                extra_pnginfo=test_extra,
            )

            # Verify _encode_one was called with metadata
            assert mock_encode.called
            # _encode_one is called with positional args: (waveform, sample_rate, fmt, quality, metadata)
            call_args = mock_encode.call_args[0]
            assert len(call_args) >= 5
            metadata = call_args[4]  # 5th positional argument is metadata
            assert isinstance(metadata, dict)
            assert "prompt" in metadata
            assert "test_key" in metadata

    def test_validate_inputs(self):
        """Test VALIDATE_INPUTS method."""
        # Test valid inputs
        assert SaveAudioExtended.VALIDATE_INPUTS(
            format="mp3",
            quality="V0",
            save_to_local=True,
            save_to_cloud=False,
        ) is True

        # Test invalid MP3 quality
        result = SaveAudioExtended.VALIDATE_INPUTS(
            format="mp3",
            quality="192k",  # Invalid for MP3
            save_to_local=True,
            save_to_cloud=False,
        )
        assert isinstance(result, str)
        assert "MP3" in result

        # Test invalid Opus quality
        result = SaveAudioExtended.VALIDATE_INPUTS(
            format="opus",
            quality="V0",  # Invalid for Opus
            save_to_local=True,
            save_to_cloud=False,
        )
        assert isinstance(result, str)
        assert "Opus" in result

        # Test both save options disabled
        result = SaveAudioExtended.VALIDATE_INPUTS(
            format="flac",
            save_to_local=False,
            save_to_cloud=False,
        )
        assert isinstance(result, str)
        assert "at least one" in result.lower()

        # Test cloud save validation
        result = SaveAudioExtended.VALIDATE_INPUTS(
            format="flac",
            save_to_local=False,
            save_to_cloud=True,
            cloud_provider="",  # Empty
            bucket_link="",
            cloud_api_key="",
        )
        assert isinstance(result, str)
        assert "cloud_provider" in result.lower()


class TestSaveAudioMP3Extended:
    """Test SaveAudioMP3Extended node."""

    def test_inherits_from_save_audio_extended(self):
        """Test that SaveAudioMP3Extended uses SaveAudioExtended implementation."""
        node = SaveAudioMP3Extended()
        assert hasattr(node, "_impl")
        assert isinstance(node._impl, SaveAudioExtended)

    def test_input_types_locks_format_to_mp3(self):
        """Test that INPUT_TYPES locks format to mp3."""
        input_types = SaveAudioMP3Extended.INPUT_TYPES()
        assert input_types["required"]["format"] == (["mp3"], {"default": "mp3"})

    def test_input_types_mp3_quality_options(self):
        """Test that INPUT_TYPES has correct MP3 quality options."""
        input_types = SaveAudioMP3Extended.INPUT_TYPES()
        quality_options = input_types["optional"]["quality"][0]
        assert "V0" in quality_options
        assert "128k" in quality_options
        assert "320k" in quality_options
        assert len(quality_options) == 3


class TestSaveAudioOpusExtended:
    """Test SaveAudioOpusExtended node."""

    def test_inherits_from_save_audio_extended(self):
        """Test that SaveAudioOpusExtended uses SaveAudioExtended implementation."""
        node = SaveAudioOpusExtended()
        assert hasattr(node, "_impl")
        assert isinstance(node._impl, SaveAudioExtended)

    def test_input_types_locks_format_to_opus(self):
        """Test that INPUT_TYPES locks format to opus."""
        input_types = SaveAudioOpusExtended.INPUT_TYPES()
        assert input_types["required"]["format"] == (["opus"], {"default": "opus"})

    def test_input_types_opus_quality_options(self):
        """Test that INPUT_TYPES has correct Opus quality options."""
        input_types = SaveAudioOpusExtended.INPUT_TYPES()
        quality_options = input_types["optional"]["quality"][0]
        assert "64k" in quality_options
        assert "96k" in quality_options
        assert "128k" in quality_options
        assert "192k" in quality_options
        assert "320k" in quality_options
        assert len(quality_options) == 5

