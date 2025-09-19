#!/usr/bin/env python3
"""A test module for Utils
"""
import unittest
from unittest.mock import patch
import utils
from parameterized import parameterized, param
from typing import List, Dict, Set, Tuple, Optional
memoize = utils.memoize


class TestAccessNestedMap(unittest.TestCase):
    """A class to test utils' access_nested_map method
    """
    @parameterized.expand([
        ({"a": 1}, ("a",), 1),
        ({"a": {"b": 2}}, ("a",), {"b": 2}),
        ({"a": {"b": 2}}, ("a", "b"), 2)
    ])
    def test_access_nested_map(self, a, b, expected) -> None:
        """A method to test that utils' access_nested_map method returns
        expected value"""
        self.assertEqual(utils.access_nested_map(a, b), expected)

    @parameterized.expand([
        ({}, ("a",), KeyError),
        ({"a": 1}, ("a", "b"), KeyError),
    ])
    def test_access_nested_map_exception(
            self, a, b, expected_exception) -> None:
        """
        A method to test that utils' access_nested_map method returns
        expected exception
        """
        with self.assertRaises(expected_exception):
            utils.access_nested_map(a, b)


class TestGetJson(unittest.TestCase):
    """A class to test utils' get_json method
    """

    def test_get_json(self) -> None:
        """A method to Mock test HTTP calls made by utils' get_json method
        """
        with patch("utils.requests.get") as mocked_get:
            test_params = [
                {"url": "http://example.com", "payload": {"payload": True}},
                {"url": "http://holberton.io", "payload": {"payload": False}}
            ]

            for url, payload in test_params:
                mocked_get.json.return_value = payload
                mocked_get.return_value = mocked_get

                mock_run = utils.get_json(url)
                mocked_get.assert_called_once_with(url)
                self.assertEqual(mock_run, payload)

                mocked_get.reset_mock()


class TestMemoize(unittest.TestCase):
    """A class to test utils' memoize
    """

    def test_memoize(self) -> None:
        """A method to test that when calling TestClass' a_property twice,
        the correct result is returned but TestClass' a_method is
        only called once.
        """
        class TestClass:
            def a_method(self):
                return 42

            @memoize
            def a_property(self):
                return self.a_method()

        test_instance = TestClass()
        with patch.object(test_instance, "a_method") as mocked_a_method:
            mocked_a_method.return_value = 42
            result1 = test_instance.a_property
            result2 = test_instance.a_property
            mocked_a_method.assert_called_once()
            self.assertEqual(result1, 42)
            self.assertEqual(result2, 42)


if __name__ == "__main__":
    unittest.main()
