"""Unit tests for the IndexManager class."""

import unittest
from datetime import datetime, timezone
from pathlib import Path

from index_manager import IndexManager


class TestIndexManager(unittest.TestCase):
    """Unit tests for the IndexManager class."""

    def setUp(self) -> None:
        """Set up a temporary database for each test."""
        self.db_path = "test_index.db"
        self.index_manager = IndexManager(db_path=self.db_path)

    def tearDown(self) -> None:
        """Clean up the temporary database after each test."""
        self.index_manager.close()
        if Path(self.db_path).exists():
            Path(self.db_path).unlink()

    def test_initialization_creates_table(self) -> None:
        """Test if the table is created upon initialization."""
        # Check if the table exists
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='local_files'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_add_and_get_file(self) -> None:
        """Test adding a file and retrieving it."""
        self.index_manager.add_file(
            file_path="/path/to/file1.txt",
            file_size=1024,
            last_modified=datetime.now(timezone.utc).isoformat(),
            md5_hash="md5hash1",
            cos_key="file1.txt",
            etag="etag1",
        )

        file_record = self.index_manager.get_file("/path/to/file1.txt")
        assert file_record is not None
        assert file_record["file_path"] == "/path/to/file1.txt"
        assert file_record["cos_key"] == "file1.txt"

    def test_get_all_files(self) -> None:
        """Test retrieving all files."""
        self.index_manager.add_file("path1", 1, "mod1", "md5_1", "key1", "etag1")
        self.index_manager.add_file("path2", 2, "mod2", "md5_2", "key2", "etag2")

        all_files = self.index_manager.get_all_files()
        assert len(all_files) == 2

    def test_remove_file(self) -> None:
        """Test removing a file."""
        self.index_manager.add_file("path1", 1, "mod1", "md5_1", "key1", "etag1")
        self.index_manager.remove_file("path1")

        file_record = self.index_manager.get_file("path1")
        assert file_record is None

    def test_file_exists(self) -> None:
        """Test checking if a file exists."""
        self.index_manager.add_file("path1", 1, "mod1", "md5_1", "key1", "etag1")

        assert self.index_manager.file_exists("key1", "etag1")
        assert not self.index_manager.file_exists("key2", "etag2")

    def test_calculate_md5(self) -> None:
        """Test the MD5 calculation."""
        # Create a dummy file
        file_path = "dummy_file.txt"
        with Path(file_path).open("w") as f:
            f.write("hello world")

        md5_hash = self.index_manager.calculate_md5(file_path)
        assert md5_hash == "5eb63bbbe01eeed093cb22bb8f5acdc3"

        Path(file_path).unlink()


if __name__ == "__main__":
    unittest.main()
