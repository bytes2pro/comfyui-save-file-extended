"""Tests for SaveImageExtended node."""

from unittest.mock import MagicMock, patch

# Import classes - conftest sets up mocks before these imports
from src.comfyui_save_file_extended.extended_nodes.save_image_extended import \
    SaveImageExtended

from .conftest import mock_folder_paths


class TestSaveImageExtended:
    """Test SaveImageExtended node."""

    def test_filename_parameter_single_image(self, save_image_node, mock_image_data, temp_dir):
        """Test that filename parameter is used when provided for single image."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_image_extended.get_uploader"):

            # Use single image
            single_image = mock_image_data[:1]

            result = save_image_node.save_images_extended(
                single_image,
                filename_prefix="test",
                filename="my_image.png",
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that the filename was used
            assert "my_image.png" in result["result"][0]
            assert result["result"][0][0] == "my_image.png"

    def test_filename_parameter_without_extension(self, save_image_node, mock_image_data, temp_dir):
        """Test that .png extension is auto-appended when filename lacks extension."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_image_extended.get_uploader"):

            single_image = mock_image_data[:1]

            result = save_image_node.save_images_extended(
                single_image,
                filename_prefix="test",
                filename="my_image",  # No extension
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that .png extension was appended
            assert "my_image.png" in result["result"][0]
            assert result["result"][0][0] == "my_image.png"

    def test_filename_parameter_batch(self, save_image_node, mock_image_data, temp_dir):
        """Test that filename parameter works correctly for batch processing."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_image_extended.get_uploader"):

            result = save_image_node.save_images_extended(
                mock_image_data,  # Batch of 2 images
                filename_prefix="test",
                filename="batch_image.png",
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that batch numbers were appended
            filenames = result["result"][0]
            assert len(filenames) == 2
            assert filenames[0] == "batch_image_000.png"
            assert filenames[1] == "batch_image_001.png"

    def test_custom_filename_parameter(self, save_image_node, mock_image_data, temp_dir):
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
             patch("src.comfyui_save_file_extended.extended_nodes.save_image_extended.get_uploader"):

            single_image = mock_image_data[:1]

            result = save_image_node.save_images_extended(
                single_image,
                filename_prefix="test",
                filename="",  # Empty filename
                custom_filename="custom_image",
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that custom_filename was used with .png extension
            assert "custom_image.png" in result["result"][0]
            assert result["result"][0][0] == "custom_image.png"

    def test_uuid_fallback(self, save_image_node, mock_image_data, temp_dir):
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
             patch("src.comfyui_save_file_extended.extended_nodes.save_image_extended.get_uploader"):

            single_image = mock_image_data[:1]

            result = save_image_node.save_images_extended(
                single_image,
                filename_prefix="test",
                filename="",  # Empty
                custom_filename="",  # Empty
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that UUID-based filename was generated
            filenames = result["result"][0]
            assert len(filenames) == 1
            assert filenames[0].startswith("test_file-")
            assert filenames[0].endswith(".png")
            # Check UUID format
            assert len(filenames[0]) > 40

    def test_filename_priority(self, save_image_node, mock_image_data, temp_dir):
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
             patch("src.comfyui_save_file_extended.extended_nodes.save_image_extended.get_uploader"):

            single_image = mock_image_data[:1]

            result = save_image_node.save_images_extended(
                single_image,
                filename_prefix="test",
                filename="priority.png",  # Should be used
                custom_filename="ignored",  # Should be ignored
                save_to_local=True,
                save_to_cloud=False,
            )

            # Check that filename was used, not custom_filename
            assert "priority.png" in result["result"][0]
            assert result["result"][0][0] == "priority.png"
            assert "ignored" not in result["result"][0][0]

    def test_local_folder_path(self, save_image_node, mock_image_data, temp_dir):
        """Test that local_folder_path creates subdirectory correctly."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        single_image = mock_image_data[:1]

        with patch("builtins.open", create=True), \
             patch("os.makedirs", create=True) as mock_makedirs, \
             patch("src.comfyui_save_file_extended.extended_nodes.save_image_extended.get_uploader"):

            result = save_image_node.save_images_extended(
                single_image,
                filename_prefix="test",
                filename="test.png",
                save_to_local=True,
                save_to_cloud=False,
                local_folder_path="images/subfolder",
            )

            # Verify makedirs was called with subfolder path
            assert mock_makedirs.called
            call_args = [str(call) for call in mock_makedirs.call_args_list]
            assert any("images/subfolder" in str(arg) for arg in call_args)

    def test_cloud_upload_enabled(self, save_image_node, mock_image_data, temp_dir):
        """Test that cloud upload is attempted when enabled."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        single_image = mock_image_data[:1]
        mock_uploader = MagicMock()
        mock_uploader.upload_many = MagicMock(return_value=[{"url": "http://example.com/file.png"}])

        with patch("builtins.open", create=True), \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_image_extended.get_uploader", return_value=mock_uploader):

            result = save_image_node.save_images_extended(
                single_image,
                filename_prefix="test",
                filename="test.png",
                save_to_local=False,
                save_to_cloud=True,
                cloud_provider="AWS S3",
                bucket_link="s3://test-bucket",
                cloud_api_key="test-key",
            )

            # Verify uploader was called
            assert mock_uploader.upload_many.called
            assert "cloud" in result
            assert len(result["cloud"]) > 0

    def test_validate_inputs_save_image_extended(self):
        """Test VALIDATE_INPUTS for SaveImageExtended (different defaults)."""
        # Test valid inputs with defaults (cloud=True, local=False)
        assert SaveImageExtended.VALIDATE_INPUTS(
            save_to_cloud=True,
            save_to_local=False,
            cloud_provider="AWS S3",
            bucket_link="s3://test",
            cloud_api_key="key",
        ) is True

        # Test both disabled (should fail)
        result = SaveImageExtended.VALIDATE_INPUTS(
            save_to_cloud=False,
            save_to_local=False,
        )
        assert isinstance(result, str)
        assert "at least one" in result.lower()

    def test_metadata_included(self, save_image_node, mock_image_data, temp_dir):
        """Test that metadata (prompt, extra_pnginfo) is included in saved images."""
        mock_folder_paths.get_save_image_path.return_value = (
            temp_dir,
            "test_file",
            0,
            "",
            "test_prefix",
        )

        single_image = mock_image_data[:1]
        test_prompt = {"test": "prompt"}
        test_extra = {"test_key": "test_value"}

        with patch("builtins.open", create=True) as mock_open, \
             patch("os.makedirs", create=True), \
             patch("src.comfyui_save_file_extended.extended_nodes.save_image_extended.get_uploader"):

            save_image_node.save_images_extended(
                single_image,
                filename_prefix="test",
                filename="test.png",
                save_to_local=True,
                save_to_cloud=False,
                prompt=test_prompt,
                extra_pnginfo=test_extra,
            )

            # Verify file was opened for writing (metadata should be included in PNG)
            assert mock_open.called

