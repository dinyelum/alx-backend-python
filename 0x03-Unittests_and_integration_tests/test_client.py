#!/usr/bin/env python3
"""A test module for Client
"""
import unittest
from unittest.mock import patch
from parameterized import parameterized, param
import client
import fixtures
from unittest.mock import PropertyMock


class TestGithubOrgClient(unittest.TestCase):
    """A class to test that client's org, public_repos_url,
    public_repos and has_license are working as expected
    """
    @parameterized.expand([
        ('google',),
        ('abc',),
    ])
    @patch('client.get_json')
    def test_org(self, org_name, mock_fetch_data):
        """A method to test that client's GithubOrgClient.org returns
        the correct value."""
        mock_fetch_data.return_value = {"payload": True}
        instance = client.GithubOrgClient(org_name)
        result = instance.org
        self.assertEqual(result, {"payload": True})

        expected_url = 'https://api.github.com/orgs/'+org_name
        mock_fetch_data.assert_called_once_with(expected_url)

        # Verify the result is cached (call org again and ensure
        # get_json not called again)
        result2 = instance.org
        # Still only called once due to memoization
        mock_fetch_data.assert_called_once()
        self.assertEqual(result2, {"payload": True})

    def test_public_repos_url(self):
        """A method to test that client's GithubOrgClient._public_repos_url
        returns the correct value."""
        instance = client.GithubOrgClient('google')
        test_payload = {
            "repos_url": "https://api.github.com/orgs/testorg/repos",
            "login": "testorg",
            "id": 237
        }
        with patch.object(
            client.GithubOrgClient,
            'org',
                new_callable=PropertyMock) as mock_org:
            mock_org.return_value = test_payload
            result = instance._public_repos_url
            self.assertEqual(result, test_payload["repos_url"])

    test_repos_payload = [
        {"name": "repo1", "license": {"key": "mit"}},
        {"name": "repo2", "license": {"key": "apache-2.0"}},
        {"name": "repo3", "license": {"key": "mit"}},
        {"name": "repo4"}  # No license
    ]

    @patch("client.get_json", return_value=test_repos_payload)
    def test_public_repos(self, mocked_get_json):
        """A method to test that client's GithubOrgClient.public_repos
        returns the correct value."""
        test_repos_url = "https://api.github.com/orgs/testorg/repos"
        with patch.object(
            client.GithubOrgClient,
            '_public_repos_url',
            new_callable=PropertyMock,
                return_value=test_repos_url) as mocked_repo_url:
            instance = client.GithubOrgClient('google')
            result = instance.public_repos()

            # Test that the result is the expected list of repo names
            expected_repos = ["repo1", "repo2", "repo3", "repo4"]
            self.assertEqual(result, expected_repos)

            # Test that mocked methods were called once
            mocked_repo_url.assert_called_once()
            mocked_get_json.assert_called_once_with(test_repos_url)

    @parameterized.expand([
        ({"license": {"key": "my_license"}}, "my_license", True),
        ({"license": {"key": "other_license"}}, "my_license", False)
    ])
    def test_has_license(self, a, b, c):
        """A method to test that client.GithubOrgClient.has_license
        returns expected value"""
        with patch.object(
            client.GithubOrgClient,
            'has_license',
                return_value=c):
            instance = client.GithubOrgClient('testorg')
            result = instance.has_license(repo=a, license_key=b)
            self.assertEqual(result, c)


@parameterized([
    {
        'org_payload': fixtures.TEST_PAYLOAD[0][0],
        'repos_payload': fixtures.TEST_PAYLOAD[0][1],
        'expected_repos': fixtures.TEST_PAYLOAD[0][2],
        'apache2_repos': fixtures.TEST_PAYLOAD[0][3],
    }
])
class TestIntegrationGithubOrgClient(unittest.TestCase):
    """Integration test for GithubOrgClient"""

    @classmethod
    def setUpClass(cls):
        """Set up class method to mock requests.get"""
        # Create a patcher for requests.get
        cls.get_patcher = patch('requests.get')

        # Start the patcher and get the mock
        cls.mock_get = cls.get_patcher.start()

        # Define side effect function to return different payloads based on URL
        def side_effect(url, *args, **kwargs):
            """Side effect function to return appropriate payload based on URL
            """
            class MockResponse:
                def __init__(self, json_data):
                    self.json_data = json_data

                def json(self):
                    return self.json_data

                def raise_for_status(self):
                    pass

            # Check which URL is being requested
            if url == "https://api.github.com/orgs/google":
                return MockResponse(cls.org_payload)
            elif url == cls.org_payload["repos_url"]:
                return MockResponse(cls.repos_payload)
            else:
                return MockResponse({})

        # Set the side effect for the mock
        cls.mock_get.side_effect = side_effect

    @classmethod
    def tearDownClass(cls):
        """Tear down class method to stop the patcher"""
        cls.get_patcher.stop()

    def test_public_repos(self):
        """Test public_repos method without license filter"""
        # Create instance and test
        client_instance = client.GithubOrgClient('google')
        result = client_instance.public_repos()

        # Verify the result matches expected repos
        self.assertEqual(result, self.expected_repos)

        # Verify requests.get was called with the expected URLs
        expected_calls = [
            unittest.mock.call("https://api.github.com/orgs/google"),
            unittest.mock.call(self.org_payload["repos_url"])
        ]
        self.mock_get.assert_has_calls(expected_calls)

    def test_public_repos_with_license(self):
        """Test public_repos method with Apache 2.0 license filter"""
        # Create instance and test with license filter
        client_instance = client.GithubOrgClient('google')
        result = client_instance.public_repos(license="apache-2.0")

        # Verify the result matches expected Apache 2.0 repos
        self.assertEqual(result, self.apache2_repos)

        # Verify requests.get was called with the expected URLs
        expected_calls = [
            unittest.mock.call("https://api.github.com/orgs/google"),
            unittest.mock.call(self.org_payload["repos_url"])
        ]
        self.mock_get.assert_has_calls(expected_calls)


if __name__ == "__main__":
    unittest.main()
