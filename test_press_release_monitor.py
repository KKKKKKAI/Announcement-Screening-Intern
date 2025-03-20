import unittest
from unittest.mock import patch, MagicMock
import requests
from bs4 import BeautifulSoup
import logging

# Importing our class to test (assuming it's in a file named press_release_monitor.py)
# If your class is in a different file, adjust this import
from press_release_monitor import PressReleaseMonitor

class TestFetchPressReleases(unittest.TestCase):
    def setUp(self):
        # Create a test instance with a dummy URL
        self.monitor = PressReleaseMonitor(url="https://example.com/press")
        
        # Create a mock logger to avoid writing to actual log files during tests
        self.mock_logger = MagicMock()
        logging.getLogger = MagicMock(return_value=self.mock_logger)

    @patch('requests.get')
    def test_successful_fetch(self, mock_get):
        # Set up mock response
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Test Press Release</h1></body></html>"
        mock_response.raise_for_status = MagicMock()  # This will do nothing when called
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.monitor.fetch_press_releases()
        
        # Check that requests.get was called with correct parameters
        mock_get.assert_called_once_with(
            "https://example.com/press",
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            timeout=30
        )
        
        # Verify the result is a BeautifulSoup object
        self.assertIsInstance(result, BeautifulSoup)
        
        # Verify the content is parsed correctly
        self.assertEqual(result.h1.text, "Test Press Release")

    @patch('requests.get')
    def test_http_error(self, mock_get):
        # Set up mock to raise an HTTP error
        mock_get.side_effect = requests.exceptions.HTTPError("404 Client Error")
        
        # Call the method
        result = self.monitor.fetch_press_releases()
        
        # Check the result is None
        self.assertIsNone(result)
        
        # Verify error was logged
        self.mock_logger.error.assert_called_once()
        # Check that the error message contains the exception text
        self.assertIn("Error fetching press releases", self.mock_logger.error.call_args[0][0])
        self.assertIn("404 Client Error", self.mock_logger.error.call_args[0][0])

    @patch('requests.get')
    def test_connection_error(self, mock_get):
        # Set up mock to raise a connection error
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        # Call the method
        result = self.monitor.fetch_press_releases()
        
        # Check the result is None
        self.assertIsNone(result)
        
        # Verify error was logged
        self.mock_logger.error.assert_called_once()
        self.assertIn("Connection refused", self.mock_logger.error.call_args[0][0])

    @patch('requests.get')
    def test_timeout_error(self, mock_get):
        # Set up mock to raise a timeout error
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        # Call the method
        result = self.monitor.fetch_press_releases()
        
        # Check the result is None
        self.assertIsNone(result)
        
        # Verify error was logged
        self.mock_logger.error.assert_called_once()
        self.assertIn("Request timed out", self.mock_logger.error.call_args[0][0])

if __name__ == '__main__':
    unittest.main()