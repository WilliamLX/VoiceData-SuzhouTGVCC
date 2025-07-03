import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
from cos_enhanced_downloader import EnhancedCOSDownloader

class TestEnhancedCOSDownloader(unittest.TestCase):
    """Unit tests for the EnhancedCOSDownloader class."""

    @patch('cos_enhanced_downloader.CosS3Client')
    @patch('cos_enhanced_downloader.IndexManager')
    def setUp(self, mock_index_manager, mock_cos_client):
        """Set up the test environment."""
        self.mock_cos_client = mock_cos_client
        self.mock_index_manager = mock_index_manager

        # Mock config file
        self.config_data = {
            "cos_config": {
                "region": "ap-guangzhou",
                "secret_id": "test_secret_id",
                "secret_key": "test_secret_key",
                "bucket_name": "test-bucket"
            },
            "options": {
                "download_dir": "test_downloads"
            }
        }
        
        # Use mock_open to simulate the config file
        m = mock_open(read_data=json.dumps(self.config_data))
        with patch('builtins.open', m):
            self.downloader = EnhancedCOSDownloader(config_file='config.json')

    def test_initialization(self):
        """Test downloader initialization."""
        self.assertIsNotNone(self.downloader.config)
        self.assertIsNotNone(self.downloader.client)
        self.assertIsNotNone(self.downloader.logger)
        self.assertIsNotNone(self.downloader.index_manager)

    def test_list_objects(self):
        """Test listing objects from COS."""
        mock_response = {
            'IsTruncated': 'false',
            'Contents': [
                {'Key': 'file1.txt', 'Size': '1024', 'ETag': '"etag1"'},
                {'Key': 'file2.mp3', 'Size': '2048', 'ETag': '"etag2"'}
            ]
        }
        self.downloader.client.list_objects.return_value = mock_response
        
        objects = self.downloader.list_objects()
        
        self.assertEqual(len(objects), 2)
        self.assertEqual(objects[0]['Key'], 'file1.txt')

    def test_download_single_file_new(self):
        """Test downloading a new file."""
        self.downloader.index_manager.file_exists.return_value = False
        
        mock_response = {'Body': MagicMock()}
        mock_response['Body'].read.return_value = b'file content'
        self.downloader.client.get_object.return_value = mock_response
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=False), \
             patch('os.makedirs'), \
             patch('os.path.getmtime', return_value=12345), \
             patch('index_manager.IndexManager.calculate_md5', return_value='mock_md5'):
            
            result = self.downloader._download_single_file(
                'file1.txt', 'local/file1.txt', 1024, 'etag1'
            )
            
            self.assertEqual(result, 'success')
            self.downloader.index_manager.add_file.assert_called_once()

    def test_download_single_file_skipped(self):
        """Test skipping an already downloaded file."""
        self.downloader.index_manager.file_exists.return_value = True
        
        result = self.downloader._download_single_file(
            'file1.txt', 'local/file1.txt', 1024, 'etag1'
        )
        
        self.assertEqual(result, 'skipped')
        self.downloader.client.get_object.assert_not_called()

    def test_download_objects(self):
        """Test downloading multiple objects."""
        objects = [
            {'Key': 'file1.txt', 'Size': '1024', 'ETag': '"etag1"'},
            {'Key': 'file2.mp3', 'Size': '2048', 'ETag': '"etag2"'}
        ]
        
        # Mock the download function to return 'success'
        with patch.object(self.downloader, '_download_single_file', return_value='success'):
            result = self.downloader.download_objects(objects, show_progress=False)
            
            self.assertEqual(result['success'], 2)
            self.assertEqual(result['failed'], 0)
            self.assertEqual(result['skipped'], 0)

if __name__ == '__main__':
    unittest.main()
