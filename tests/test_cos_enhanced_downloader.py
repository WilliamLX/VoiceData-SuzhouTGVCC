"""Unit tests for the EnhancedCOSDownloader class."""

import unittest
from unittest.mock import MagicMock, mock_open, patch

from cos_enhanced_downloader import EnhancedCOSDownloader


class TestEnhancedCOSDownloader(unittest.TestCase):
    """Unit tests for the EnhancedCOSDownloader class."""

    @patch("cos_enhanced_downloader.CosS3Client")
    @patch("cos_enhanced_downloader.IndexManager")
    def setUp(self, mock_index_manager: MagicMock, mock_cos_client: MagicMock) -> None:
        """Set up the test environment."""
        self.mock_cos_client = mock_cos_client
        self.mock_index_manager = mock_index_manager

        # Mock the config loading
        mock_config = {
            "secret_id": "test_id",
            "secret_key": "test_key",
            "region": "ap-beijing",
            "bucket": "test-bucket",
        }

        with (
            patch(
                "builtins.open",
                mock_open(
                    read_data='{"secret_id": "test_id", "secret_key": "test_key", "region": "ap-beijing", "bucket": "test-bucket"}'
                ),
            ),
            patch("json.load", return_value=mock_config),
            patch("cos_enhanced_downloader.CosConfig"),
            patch("cos_enhanced_downloader.logging.getLogger"),
            patch(
                "cos_enhanced_downloader.IndexManager", return_value=mock_index_manager
            ),
        ):
            self.downloader = EnhancedCOSDownloader(config_file="config.json")

    def test_initialization(self) -> None:
        """Test downloader initialization."""
        assert self.downloader.config is not None
        assert self.downloader.client is not None
        assert self.downloader.logger is not None
        assert self.downloader.index_manager is not None

    def test_list_objects(self) -> None:
        """Test listing objects from COS."""
        mock_response = {
            "Contents": [
                {"Key": "file1.txt", "Size": 1024, "ETag": '"etag1"'},
                {"Key": "file2.txt", "Size": 2048, "ETag": '"etag2"'},
            ]
        }

        self.downloader.client.list_objects.return_value = mock_response

        objects = self.downloader.list_objects()

        assert len(objects) == 2
        assert objects[0]["Key"] == "file1.txt"

    def test_download_single_file_new(self) -> None:
        """Test downloading a new file."""
        self.downloader.index_manager.file_exists.return_value = False

        mock_response = MagicMock()
        mock_response["Body"].read.return_value = b"test content"
        self.downloader.client.get_object.return_value = mock_response

        with (
            patch("builtins.open", mock_open()) as mock_file,
            patch("os.path.exists", return_value=False),
            patch("os.makedirs"),
            patch("index_manager.IndexManager.calculate_md5", return_value="mock_md5"),
        ):
            result = self.downloader._download_single_file(
                "file1.txt", "local/file1.txt", 1024, "etag1"
            )

            assert result == "success"
            self.downloader.index_manager.add_file.assert_called_once()

    def test_download_single_file_skipped(self) -> None:
        """Test skipping an already downloaded file."""
        self.downloader.index_manager.file_exists.return_value = True

        result = self.downloader._download_single_file(
            "file1.txt", "local/file1.txt", 1024, "etag1"
        )

        assert result == "skipped"
        self.downloader.client.get_object.assert_not_called()

    def test_download_objects(self) -> None:
        """Test downloading multiple objects."""
        objects = [
            {"Key": "file1.txt", "Size": 1024, "ETag": '"etag1"'},
            {"Key": "file2.txt", "Size": 2048, "ETag": '"etag2"'},
        ]

        self.downloader.index_manager.file_exists.return_value = False

        mock_response = MagicMock()
        mock_response["Body"].read.return_value = b"test content"
        self.downloader.client.get_object.return_value = mock_response

        with (
            patch("builtins.open", mock_open()),
            patch("os.path.exists", return_value=False),
            patch("os.makedirs"),
            patch("index_manager.IndexManager.calculate_md5", return_value="mock_md5"),
        ):
            result = self.downloader.download_objects(objects, show_progress=False)

            assert result["success"] == 2
            assert result["failed"] == 0
            assert result["skipped"] == 0


if __name__ == "__main__":
    unittest.main()
