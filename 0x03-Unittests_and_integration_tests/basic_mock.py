import unittest
from unittest.mock import patch


class MyModule:
    def fetch_data(self):
        # Imagine this makes a network call
        return "Real Data"


class MyTest(unittest.TestCase):
    @patch('my_module.MyModule.fetch_data', return_value="Mocked Data")
    def test_fetch_data_mocked(self, mock_fetch_data):
        instance = MyModule()
        result = instance.fetch_data()
        self.assertEqual(result, "Mocked Data")
        mock_fetch_data.assert_called_once()
