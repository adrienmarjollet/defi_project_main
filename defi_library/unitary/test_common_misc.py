import tempfile
import shutil
import os

import unittest
from pyfixture import fixture

from pathlib import Path
from unittest.mock import patch

# Import the functions to be tested
from common.misc import find_project_root_path, load_env_variables


class TestFindProjectRootPath(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_marker_file_in_current_directory(self):
        # Create a marker file in the current directory
        marker_file = 'pyproject.toml'
        (Path(self.test_dir) / marker_file).touch()

        # Change the current working directory to the test directory
        os.chdir(self.test_dir)

        # Test the function
        result = find_project_root_path(marker_file)
        self.assertEqual(result, Path(self.test_dir))

    def test_marker_file_in_parent_directory(self):
        # Create a nested directory structure
        nested_dir = Path(self.test_dir) / 'nested' / 'subdir'
        nested_dir.mkdir(parents=True)

        # Create a marker file in the parent directory
        marker_file = 'pyproject.toml'
        (Path(self.test_dir) / marker_file).touch()

        # Change the current working directory to the nested directory
        os.chdir(nested_dir)

        # Test the function
        result = find_project_root_path(marker_file)
        self.assertEqual(result, Path(self.test_dir))

    def test_marker_file_not_found(self):
        # Change the current working directory to the test directory
        os.chdir(self.test_dir)

        # Test that the function raises FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            find_project_root_path('nonexistent_file.txt')


@fixture
def setup_env_file():
    # Create a temporary directory and .env file
    temp_dir = tempfile.mkdtemp()
    env_file_path = os.path.join(temp_dir, '.env')
    with open(env_file_path, 'w') as f:
        f.write('VAR1=value1\nVAR2=value2\n')
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir)



class TestLoadEnvVariables(unittest.TestCase):

    @patch('defi_library.common.misc.load_dotenv')
    @patch('defi_library.common.misc.os.getenv')
    def test_load_env_variables(self, mock_getenv, mock_load_dotenv, setup_env_file):
        # Setup the mock for os.getenv
        mock_getenv.side_effect = lambda key: {
            'VAR1': 'value1',
            'VAR2': 'value2'
        }.get(key, None)

        # Define the root path and list of environment variables
        root_path = setup_env_file
        list_env_vars = ['VAR1', 'VAR2']

        # Call the function
        result = load_env_variables(root_path, list_env_vars)

        # Assertions
        self.assertEqual(result, ['value1', 'value2'])
        mock_load_dotenv.assert_called_once_with(os.path.join(root_path, '.env'))
        mock_getenv.assert_any_call('VAR1')
        mock_getenv.assert_any_call('VAR2')

    @patch('defi_library.common.misc.load_dotenv')
    @patch('defi_library.common.misc.os.getenv')
    def test_load_env_variables_missing_var(self, mock_getenv, mock_load_dotenv, setup_env_file):
        # Setup the mock for os.getenv
        mock_getenv.side_effect = lambda key: {
            'VAR1': 'value1'
        }.get(key, None)

        # Define the root path and list of environment variables
        root_path = setup_env_file
        list_env_vars = ['VAR1', 'VAR2']

        # Call the function and assert it raises ValueError
        with self.assertRaises(ValueError) as context:
            load_env_variables(root_path, list_env_vars)

        self.assertEqual(str(context.exception), 'VAR2 is not set in the .env file')
        mock_load_dotenv.assert_called_once_with(os.path.join(root_path, '.env'))
        mock_getenv.assert_any_call('VAR1')
        mock_getenv.assert_any_call('VAR2')



if __name__ == '__main__':
    unittest.main()