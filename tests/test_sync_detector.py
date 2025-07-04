"""Unit tests for the SyncDetector class."""

import unittest
from unittest.mock import MagicMock

from sync_detector import SyncDetector


class TestSyncDetector(unittest.TestCase):
    """Unit tests for the SyncDetector class."""

    def setUp(self) -> None:
        """Set up the test environment."""
        self.mock_cos_client = MagicMock()
        self.mock_index_manager = MagicMock()
        self.detector = SyncDetector(self.mock_cos_client, self.mock_index_manager)

    def test_compare_objects(self) -> None:
        """Test the comparison of remote and local objects."""
        remote_objects = [
            {"Key": "file1.txt", "ETag": '"etag1"'},
            {"Key": "file2.txt", "ETag": '"new_etag"'},
            {"Key": "file3.txt", "ETag": '"etag3"'},
        ]

        local_files = [
            {"cos_key": "file1.txt", "etag": "etag1"},
            {"cos_key": "file2.txt", "etag": "old_etag"},
            # file4.txt is local only
            {"cos_key": "file4.txt", "etag": "etag4"},
        ]

        self.mock_cos_client.list_objects.return_value = {"Contents": remote_objects}
        self.mock_index_manager.get_all_files.return_value = local_files

        # Run the comparison
        diff = self.detector.compare_objects(remote_objects, local_files)

        # Check the results
        assert len(diff["new"]) == 1
        assert diff["new"][0]["Key"] == "file3.txt"

        assert len(diff["updated"]) == 1
        assert diff["updated"][0]["Key"] == "file2.txt"

        # For now, 'deleted' is a placeholder
        assert len(diff["deleted"]) == 0


if __name__ == "__main__":
    unittest.main()
