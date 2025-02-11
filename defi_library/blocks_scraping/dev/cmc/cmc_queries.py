import requests


# dev imports
from config import CMC_API_KEY

from common.misc import find_project_root_path, load_env_variables


class CmcQueries:
    def __init__(self):
        self.root_path = find_project_root_path()
        self._cmc_api_key = load_env_variables(self.root_path, [CMC_API_KEY])[0]

    def get_cryptocurrency_map(self, start: int = 1, limit: int = 1):
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/map"
        parameters = {
            "start": start,
            "limit": str(limit),
        }
        headers = {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": self._cmc_api_key,
        }

        response = requests.get(url, headers=headers, params=parameters)
        response.raise_for_status()

        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    def get_coin_data(self, start: int = 1, limit: int = 1):
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        parameters = {
            "start": start,
            "limit": str(limit),
        }
        headers = {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": self._cmc_api_key,
        }
        response = requests.get(url, headers=headers, params=parameters)
        # make to a json
        data = response.json()
        return data["data"]


if __name__ == "__main__":
    print("Testing the functions in cmc_queries.py")
    print("---------------------------------")
    cmc_queries = CmcQueries()
    print("--> get_cryptocurrency_map")
    print(cmc_queries.get_cryptocurrency_map())
    print("--> get_coin_price")
    print(cmc_queries.get_coin_data())
