import tempfile
import shutil
import os

import unittest
from pyfixture import fixture

from pathlib import Path
from unittest.mock import patch

# Import the functions to be unittested
from common.misc import find_project_root_path, load_env_variables

class TestFindProjectRootPath(unittest.TestCase):


    def setUp(self): # this method is called BEFORE each test (framework unittest rules from Method names)
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        # Save the current working directory
        self.original_cwd = os.getcwd()


    def tearDown(self): # this method is called AFTER each test (framework unittest rules from Method names)
        # Change back to the original working directory
        os.chdir(self.original_cwd)
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)


    def test_return_path_object(self): # methods starting with test_ are run by unittest
        # The function should return a Path object
        result = find_project_root_path()
        self.assertIsInstance(result, Path)    


    def test_marker_file_in_current_directory(self): # methods starting with test_ are run by unittest
        # Create a marker file in the current directory
        marker_file_test = 'test_marker.toml'
        (Path(self.test_dir) / marker_file_test).touch()

        # Change the current working directory to the test directory
        os.chdir(self.test_dir)

        # Test the function
        result = find_project_root_path(marker_file=marker_file_test)
        self.assertEqual(result, Path(self.test_dir))


    def test_marker_file_in_parent_directory(self): # methods starting with test_ are run by unittest
        # Create a nested directory structure
        nested_dir = Path(self.test_dir) / 'nested' / 'subdir'
        nested_dir.mkdir(parents=True)

        # Create a marker file in the parent directory
        marker_file_test = 'test_marker.toml'
        (Path(self.test_dir) / marker_file_test).touch()

        # Change the current working directory to the nested directory
        os.chdir(nested_dir)

        # Test the function
        result = find_project_root_path(marker_file=marker_file_test)
        self.assertEqual(result, Path(self.test_dir))


    def test_marker_file_not_found(self): # methods starting with test_ are run by unittest
        # Change the current working directory to the test directory
        os.chdir(self.test_dir)

        # Test that the function raises FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            find_project_root_path('nonexistent_file.txt')



class TestLoadEnvVariables(unittest.TestCase):


    def setUp(self):
        # Create a temporary directory and .env file
        self.temp_dir = tempfile.mkdtemp()
        self.env_file_path = os.path.join(self.temp_dir, '.env')
        with open(self.env_file_path, 'w') as f:
            f.write('VAR1=value1\nVAR2=value2\n')


    def tearDown(self):
        # Cleanup the temporary directory
        shutil.rmtree(self.temp_dir)


    @patch('common.misc.load_dotenv')
    @patch('common.misc.os.getenv')
    def test_load_env_variables(self, mock_getenv, mock_load_dotenv):
        # Setup the mock for os.getenv
        mock_getenv.side_effect = lambda key: {
            'VAR1': 'value1',
            'VAR2': 'value2'
        }.get(key, None)

        # Define the root path and list of environment variables
        root_path = self.temp_dir
        list_env_vars = ['VAR1', 'VAR2']

        # Call the function
        result = load_env_variables(root_path, list_env_vars)

        # Assertions
        self.assertEqual(result, ['value1', 'value2'])
        mock_load_dotenv.assert_called_once_with(os.path.join(root_path, '.env'))
        mock_getenv.assert_any_call('VAR1')
        mock_getenv.assert_any_call('VAR2')


    @patch('common.misc.load_dotenv')
    @patch('common.misc.os.getenv')
    def test_load_env_variables_missing_var(self, mock_getenv, mock_load_dotenv):
        # Setup the mock for os.getenv
        mock_getenv.side_effect = lambda key: {
            'VAR1': 'value1'
        }.get(key, None)

        # Define the root path and list of environment variables
        root_path = self.temp_dir
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