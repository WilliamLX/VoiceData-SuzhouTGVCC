import sqlite3
import os
import hashlib
from datetime import datetime

class IndexManager:
    """Manages a local index of downloaded files using SQLite."""

    def __init__(self, db_path='download_index.db'):
        """
        Initializes the IndexManager.

        Args:
            db_path (str): The path to the SQLite database file.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        """Creates the 'local_files' table if it doesn't exist."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS local_files (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT UNIQUE NOT NULL,
                    file_size INTEGER NOT NULL,
                    last_modified TEXT NOT NULL,
                    md5_hash TEXT NOT NULL,
                    download_time TEXT NOT NULL,
                    cos_key TEXT NOT NULL,
                    etag TEXT
                )
            """)

    def add_file(self, file_path, file_size, last_modified, md5_hash, cos_key, etag):
        """
        Adds a file record to the index.

        Args:
            file_path (str): Absolute path of the downloaded file.
            file_size (int): Size of the file in bytes.
            last_modified (str): Last modified timestamp (ISO 8601 format).
            md5_hash (str): MD5 hash of the file.
            cos_key (str): The object key in COS.
            etag (str): The ETag of the object from COS.
        """
        download_time = datetime.now().isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO local_files 
                (file_path, file_size, last_modified, md5_hash, download_time, cos_key, etag)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (file_path, file_size, last_modified, md5_hash, download_time, cos_key, etag))

    def get_file(self, file_path):
        """
        Retrieves a file record by its path.

        Args:
            file_path (str): The path of the file to retrieve.

        Returns:
            A dict-like row object if the file is found, otherwise None.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM local_files WHERE file_path = ?", (file_path,))
        return cursor.fetchone()

    def get_all_files(self):
        """
        Retrieves all file records from the index.

        Returns:
            A list of dict-like row objects.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM local_files")
        return cursor.fetchall()

    def remove_file(self, file_path):
        """
        Removes a file record from the index.

        Args:
            file_path (str): The path of the file to remove.
        """
        with self.conn:
            self.conn.execute("DELETE FROM local_files WHERE file_path = ?", (file_path,))

    def file_exists(self, cos_key, etag):
        """
        Checks if a file with a given COS key and ETag already exists.

        Args:
            cos_key (str): The object key in COS.
            etag (str): The ETag of the object from COS.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM local_files WHERE cos_key = ? AND etag = ?", (cos_key, etag))
        return cursor.fetchone() is not None

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()

    @staticmethod
    def calculate_md5(file_path):
        """
        Calculates the MD5 hash of a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            str: The hex digest of the MD5 hash.
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
