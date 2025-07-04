"""Index manager for tracking downloaded files."""

import hashlib
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class IndexManager:
    """Manages a local index of downloaded files using SQLite."""

    def __init__(self, db_path: str = "download_index.db") -> None:
        """
        Initialize the IndexManager.

        Args:
            db_path: The path to the SQLite database file.
        """
        self.db_path = db_path
        self._local = threading.local()
        self._create_table()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection for current thread."""
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _create_table(self) -> None:
        """Create the 'local_files' table if it doesn't exist."""
        conn = self._get_connection()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS local_files (
                    file_path TEXT PRIMARY KEY,
                    file_size INTEGER,
                    last_modified TEXT,
                    md5_hash TEXT,
                    download_time TEXT,
                    cos_key TEXT,
                    etag TEXT
                )
            """)

    def add_file(
        self,
        file_path: str,
        file_size: int,
        last_modified: str,
        md5_hash: str,
        cos_key: str,
        etag: str,
    ) -> None:
        """
        Add a file record to the index.

        Args:
            file_path: Absolute path of the downloaded file.
            file_size: Size of the file in bytes.
            last_modified: Last modified timestamp (ISO 8601 format).
            md5_hash: MD5 hash of the file.
            cos_key: The object key in COS.
            etag: The ETag of the object from COS.
        """
        download_time = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO local_files
                (file_path, file_size, last_modified, md5_hash, download_time, cos_key, etag)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    file_path,
                    file_size,
                    last_modified,
                    md5_hash,
                    download_time,
                    cos_key,
                    etag,
                ),
            )

    def get_file(self, file_path: str) -> Optional[sqlite3.Row]:
        """
        Retrieve a file record by its path.

        Args:
            file_path: The path of the file to retrieve.

        Returns:
            A dict-like row object if the file is found, otherwise None.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM local_files WHERE file_path = ?", (file_path,))
        return cursor.fetchone()

    def get_all_files(self) -> List[sqlite3.Row]:
        """
        Retrieve all file records from the index.

        Returns:
            A list of dict-like row objects.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM local_files")
        return cursor.fetchall()

    def remove_file(self, file_path: str) -> None:
        """
        Remove a file record from the index.

        Args:
            file_path: The path of the file to remove.
        """
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM local_files WHERE file_path = ?", (file_path,))

    def file_exists(self, cos_key: str, etag: str) -> bool:
        """
        Check if a file with a given COS key and ETag already exists.

        Args:
            cos_key: The object key in COS.
            etag: The ETag of the object from COS.

        Returns:
            True if the file exists, False otherwise.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM local_files WHERE cos_key = ? AND etag = ?", (cos_key, etag)
        )
        return cursor.fetchone() is not None

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, "conn"):
            self._local.conn.close()

    @staticmethod
    def calculate_md5(file_path: str) -> str:
        """
        Calculate the MD5 hash of a file.

        Args:
            file_path: The path to the file.

        Returns:
            The hex digest of the MD5 hash.
        """
        hash_md5 = hashlib.md5()
        with Path(file_path).open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
