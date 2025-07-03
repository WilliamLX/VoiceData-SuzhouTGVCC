import unittest
import os
import sqlite3
from datetime import datetime
from index_manager import IndexManager

class TestIndexManager(unittest.TestCase):
    """Unit tests for the IndexManager class."""

    def setUp(self):
        """Set up a temporary database for each test."""
        self.db_path = 'test_index.db'
        self.index_manager = IndexManager(db_path=self.db_path)

    def tearDown(self):
        """Clean up the temporary database after each test."""
        self.index_manager.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_initialization_creates_table(self):
        """Test if the table is created upon initialization."""
        # Check if the table exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='local_files'")
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_add_and_get_file(self):
        """Test adding a file and retrieving it."""
        self.index_manager.add_file(
            file_path='/path/to/file1.txt',
            file_size=1024,
            last_modified=datetime.now().isoformat(),
            md5_hash='md5hash1',
            cos_key='file1.txt',
            etag='etag1'
        )
        
        file_record = self.index_manager.get_file('/path/to/file1.txt')
        self.assertIsNotNone(file_record)
        self.assertEqual(file_record['file_path'], '/path/to/file1.txt')
        self.assertEqual(file_record['cos_key'], 'file1.txt')

    def test_get_all_files(self):
        """Test retrieving all files."""
        self.index_manager.add_file('path1', 1, 'mod1', 'md5_1', 'key1', 'etag1')
        self.index_manager.add_file('path2', 2, 'mod2', 'md5_2', 'key2', 'etag2')
        
        all_files = self.index_manager.get_all_files()
        self.assertEqual(len(all_files), 2)

    def test_remove_file(self):
        """Test removing a file."""
        self.index_manager.add_file('path1', 1, 'mod1', 'md5_1', 'key1', 'etag1')
        self.index_manager.remove_file('path1')
        
        file_record = self.index_manager.get_file('path1')
        self.assertIsNone(file_record)

    def test_file_exists(self):
        """Test checking if a file exists."""
        self.index_manager.add_file('path1', 1, 'mod1', 'md5_1', 'key1', 'etag1')
        
        self.assertTrue(self.index_manager.file_exists('key1', 'etag1'))
        self.assertFalse(self.index_manager.file_exists('key2', 'etag2'))

    def test_calculate_md5(self):
        """Test the MD5 calculation."""
        # Create a dummy file
        file_path = 'dummy_file.txt'
        with open(file_path, 'w') as f:
            f.write('hello world')
            
        md5_hash = self.index_manager.calculate_md5(file_path)
        self.assertEqual(md5_hash, '5eb63bbbe01eeed093cb22bb8f5acdc3')
        
        os.remove(file_path)

if __name__ == '__main__':
    unittest.main()
