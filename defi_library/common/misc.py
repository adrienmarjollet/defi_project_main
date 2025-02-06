import os
from pathlib import Path
from dotenv import load_dotenv

############
## GENERAL FUNCTIONS
#############


def find_project_root_path(marker_file='pyproject.toml'):
    current_path = Path(__file__).resolve().parent
    for parent in current_path.parents:
        if (parent / marker_file).exists():
            return parent
    raise FileNotFoundError(f'{marker_file} not found in the directory tree')



def load_env_variables(root_path, list_env_vars):
    """ 
    Load the environment variables from the .env file
    Return them as a list
    """

    env_vars_path = os.path.join(root_path, '.env')

    load_dotenv(env_vars_path)

    l_values = []

    for env_var in list_env_vars:
        env_var_value = os.getenv(env_var)
        if env_var_value is None:
            raise ValueError(f'{env_var} is not set in the .env file')
        else:
            print(f'Env variable {env_var} loaded.')
            l_values.append(env_var_value)

    return l_values        


if __name__ == '__main__':
    print('Testing the functions in misc.py')
    print('---------------------------------')
    print('find_project_root_path')
    root_path = find_project_root_path()
    print('root_path:', root_path)
    print('---------------------------------')
    print('load_env_variables')
    list_env_vars = ['PYTHONPATH']
    print(load_env_variables(root_path, list_env_vars))