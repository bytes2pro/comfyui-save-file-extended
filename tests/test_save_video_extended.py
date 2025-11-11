"""Tests for SaveVideoExtended and SaveWEBMExtended nodes."""

import os
from unittest.mock import MagicMock, patch

# Import classes - conftest sets up mocks before these imports
from src.comfyui_save_file_extended.extended_nodes.save_video_extended import (
    SaveVideoExtended, SaveWEBMExtended)

from .conftest import mock_folder_paths


class TestSaveWEBMExtended:
    """Test SaveWEBMExtended node."""

    def test_filename_parameter(self, save_webm_node, mock_image_data, temp_dir):
        """Test that filename parameter is used when provided."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            result = save_webm_node.save_images(
                mock_image_data,
                codec="vp9",
                fps=24.0,
                filename_prefix="test",
                crf=32.0,
                filename="my_video.webm",
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that the filename was used
            assert "my_video.webm" in result["result"][0]
            assert result["result"][0][0] == "my_video.webm"

    def test_filename_parameter_without_extension(self, save_webm_node, mock_image_data, temp_dir):
        """Test that .webm extension is auto-appended when filename lacks extension."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            result = save_webm_node.save_images(
                mock_image_data,
                codec="vp9",
                fps=24.0,
                filename_prefix="test",
                crf=32.0,
                filename="my_video",  # No extension
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that .webm extension was appended
            assert "my_video.webm" in result["result"][0]
            assert result["result"][0][0] == "my_video.webm"

    def test_custom_filename_parameter(self, save_webm_node, mock_image_data, temp_dir):
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
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            result = save_webm_node.save_images(
                mock_image_data,
                codec="av1",
                fps=30.0,
                filename_prefix="test",
                crf=28.0,
                filename="",  # Empty filename
                custom_filename="custom_video",
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that custom_filename was used with .webm extension
            assert "custom_video.webm" in result["result"][0]
            assert result["result"][0][0] == "custom_video.webm"

    def test_uuid_fallback(self, save_webm_node, mock_image_data, temp_dir):
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
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            result = save_webm_node.save_images(
                mock_image_data,
                codec="vp9",
                fps=24.0,
                filename_prefix="test",
                crf=32.0,
                filename="",  # Empty
                custom_filename="",  # Empty
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that UUID-based filename was generated
            filenames = result["result"][0]
            assert len(filenames) == 1
            assert filenames[0].startswith("test_file-")
            assert filenames[0].endswith(".webm")
            # Check UUID format
            assert len(filenames[0]) > 40

    def test_validate_inputs_save_webm_extended(self):
        """Test VALIDATE_INPUTS for SaveWEBMExtended."""
        # Test valid inputs
        assert SaveWEBMExtended.VALIDATE_INPUTS(
            codec="vp9",
            fps=24.0,
            crf=32.0,
            save_to_local=True,
            save_to_cloud=False,
        ) is True

        # Test both save options disabled
        result = SaveWEBMExtended.VALIDATE_INPUTS(
            codec="vp9",
            fps=24.0,
            crf=32.0,
            save_to_local=False,
            save_to_cloud=False,
        )
        assert isinstance(result, str)
        assert "at least one" in result.lower()

    def test_local_folder_path(self, save_webm_node, mock_image_data, temp_dir):
        """Test that local_folder_path creates subdirectory correctly."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        # Use side_effect to actually create directories while tracking calls
        original_makedirs = os.makedirs
        makedirs_calls = []
        
        def makedirs_side_effect(path, *args, **kwargs):
            makedirs_calls.append(path)
            return original_makedirs(path, *args, **kwargs)

        with patch("builtins.open", create=True), \
             patch("os.makedirs", side_effect=makedirs_side_effect), \
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            result = save_webm_node.save_images(
                mock_image_data,
                codec="vp9",
                fps=24.0,
                filename_prefix="test",
                crf=32.0,
                filename="test.webm",
                save_to_local=True,
                save_to_cloud=False,
                local_folder_path="videos/subfolder",
            )

            # Verify makedirs was called with subfolder path
            assert len(makedirs_calls) > 0
            assert any("videos/subfolder" in str(path) for path in makedirs_calls)


class TestSaveVideoExtended:
    """Test SaveVideoExtended node."""

    def test_filename_parameter(self, save_video_node, mock_video_data, temp_dir):
        """Test that filename parameter is used when provided."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            result = save_video_node.save_video(
                mock_video_data,
                filename_prefix="test",
                format="mp4",
                codec="h264",
                filename="my_video.mp4",
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that the filename was used
            assert "my_video.mp4" in result["result"][0]
            assert result["result"][0][0] == "my_video.mp4"
            # Verify video.save_to was called with correct path
            mock_video_data.save_to.assert_called_once()

    def test_filename_parameter_without_extension(self, save_video_node, mock_video_data, temp_dir):
        """Test that extension is auto-appended based on format when filename lacks extension."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        # get_extension will return mp4 for format="mp4" (already configured in mock)

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            result = save_video_node.save_video(
                mock_video_data,
                filename_prefix="test",
                format="mp4",
                codec="h264",
                filename="my_video",  # No extension
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that extension was appended
            assert "my_video.mp4" in result["result"][0]
            assert result["result"][0][0] == "my_video.mp4"

    def test_custom_filename_parameter(self, save_video_node, mock_video_data, temp_dir):
        """Test that custom_filename parameter works when filename is empty."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        # get_extension will return webm for format="webm" (already configured in mock)

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            result = save_video_node.save_video(
                mock_video_data,
                filename_prefix="test",
                format="webm",
                codec="vp9",
                filename="",  # Empty filename
                custom_filename="custom_video",
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that custom_filename was used with format extension
            assert "custom_video.webm" in result["result"][0]
            assert result["result"][0][0] == "custom_video.webm"

    def test_uuid_fallback(self, save_video_node, mock_video_data, temp_dir):
        """Test that UUID-based filename is used when both filename and custom_filename are empty."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        # get_extension will return mkv for format="mkv" (already configured in mock)

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            result = save_video_node.save_video(
                mock_video_data,
                filename_prefix="test",
                format="mkv",
                codec="h264",
                filename="",  # Empty
                custom_filename="",  # Empty
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that UUID-based filename was generated
            filenames = result["result"][0]
            assert len(filenames) == 1
            assert filenames[0].startswith("test_file-")
            assert filenames[0].endswith(".mkv")
            # Check UUID format
            assert len(filenames[0]) > 40

    def test_filename_priority(self, save_video_node, mock_video_data, temp_dir):
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
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            result = save_video_node.save_video(
                mock_video_data,
                filename_prefix="test",
                format="mp4",
                codec="h264",
                filename="priority.mp4",  # Should be used
                custom_filename="ignored",  # Should be ignored
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that filename was used, not custom_filename
            assert "priority.mp4" in result["result"][0]
            assert result["result"][0][0] == "priority.mp4"
            assert "ignored" not in result["result"][0][0]

    def test_whitespace_only_filename(self, save_video_node, mock_video_data, temp_dir):
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
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            result = save_video_node.save_video(
                mock_video_data,
                filename_prefix="test",
                format="mp4",
                codec="h264",
                filename="   ",  # Whitespace only
                custom_filename="fallback",
                save_to_local=True,
                save_to_cloud=False,
            )

            # Should fall back to custom_filename
            assert "fallback.mp4" in result["result"][0]
            assert result["result"][0][0] == "fallback.mp4"

    def test_validate_inputs(self):
        """Test VALIDATE_INPUTS method."""
        # Test valid inputs
        assert SaveVideoExtended.VALIDATE_INPUTS(
            format="mp4",
            codec="h264",
            save_to_local=True,
            save_to_cloud=False,
        ) is True

        # Test both save options disabled
        result = SaveVideoExtended.VALIDATE_INPUTS(
            format="mp4",
            codec="h264",
            save_to_local=False,
            save_to_cloud=False,
        )
        assert isinstance(result, str)
        assert "at least one" in result.lower()

        # Test cloud save without required fields
        result = SaveVideoExtended.VALIDATE_INPUTS(
            format="mp4",
            codec="h264",
            save_to_local=False,
            save_to_cloud=True,
            cloud_provider="",  # Empty
            bucket_link="",
            cloud_api_key="",
        )
        assert isinstance(result, str)
        assert "cloud_provider" in result.lower()

        # Test cloud save with provider but no bucket
        result = SaveVideoExtended.VALIDATE_INPUTS(
            format="mp4",
            codec="h264",
            save_to_local=False,
            save_to_cloud=True,
            cloud_provider="AWS S3",
            bucket_link="",  # Empty
            cloud_api_key="test_key",
        )
        assert isinstance(result, str)
        assert "bucket_link" in result.lower()

        # Test cloud save with provider and bucket but no API key
        result = SaveVideoExtended.VALIDATE_INPUTS(
            format="mp4",
            codec="h264",
            save_to_local=False,
            save_to_cloud=True,
            cloud_provider="AWS S3",
            bucket_link="test-bucket",
            cloud_api_key="",  # Empty
        )
        assert isinstance(result, str)
        assert "cloud_api_key" in result.lower()

    def test_different_formats(self, save_video_node, mock_video_data, temp_dir):
        """Test that different video formats work correctly."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        formats_to_test = [
            ("mp4", "mp4"),
            ("webm", "webm"),
            ("mkv", "mkv"),
            ("auto", "mp4"),  # auto should default to mp4
        ]

        for format_value, expected_ext in formats_to_test:
            with patch("builtins.open", create=True), \
                 patch("os.makedirs", create=True), \
                 patch("os.remove", create=True), \
                 patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

                result = save_video_node.save_video(
                    mock_video_data,
                    filename_prefix="test",
                    format=format_value,
                    codec="h264",
                    filename="",  # Empty
                    custom_filename=f"test_{format_value}",
                    save_to_local=True,
                    save_to_cloud=False,
                )

                # Check that correct extension was used
                assert result["result"][0][0] == f"test_{format_value}.{expected_ext}"

    def test_local_folder_path(self, save_video_node, mock_video_data, temp_dir):
        """Test that local_folder_path creates subdirectory correctly."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True), \
             patch("os.makedirs", create=True) as mock_makedirs, \
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            result = save_video_node.save_video(
                mock_video_data,
                filename_prefix="test",
                format="mp4",
                codec="h264",
                filename="test.mp4",
                save_to_local=True,
                save_to_cloud=False,
                local_folder_path="videos/subfolder",
            )

            # Verify makedirs was called with subfolder path
            assert mock_makedirs.called
            call_args = [str(call) for call in mock_makedirs.call_args_list]
            assert any("videos/subfolder" in str(arg) for arg in call_args)

    def test_cloud_upload_enabled(self, save_video_node, mock_video_data, temp_dir):
        """Test that cloud upload is attempted when enabled."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        mock_uploader = MagicMock()
        mock_uploader.upload_many = MagicMock(return_value=[{"url": "http://example.com/file.mp4"}])

        with patch("builtins.open", create=True), \
             patch("os.makedirs", create=True), \
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader", return_value=mock_uploader):

            result = save_video_node.save_video(
                mock_video_data,
                filename_prefix="test",
                format="mp4",
                codec="h264",
                filename="test.mp4",
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

    def test_metadata_included(self, save_video_node, mock_video_data, temp_dir):
        """Test that metadata (prompt, extra_pnginfo) is passed to video.save_to."""
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
             patch("os.remove", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_video_extended.get_uploader"):

            save_video_node.save_video(
                mock_video_data,
                filename_prefix="test",
                format="mp4",
                codec="h264",
                filename="test.mp4",
                save_to_local=True,
                save_to_cloud=False,
                prompt=test_prompt,
                extra_pnginfo=test_extra,
            )

            # Verify video.save_to was called with metadata
            assert mock_video_data.save_to.called
            call_kwargs = mock_video_data.save_to.call_args[1]
            assert "metadata" in call_kwargs
            metadata = call_kwargs["metadata"]
            assert metadata is not None
            assert "prompt" in metadata
            assert "test_key" in metadata

