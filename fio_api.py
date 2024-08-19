#!/usr/bin/env python3

import requests
import json
import pandas as pd
import re
import os
from io import StringIO
from urllib.parse import urlencode, urlparse, quote_plus
from datetime import datetime, timedelta

MAX_RETRIES = 3

class FIOAPI:
    def __init__(self, api_key_file='./apikey.txt'):
        self.api_key = self._read_api_key(api_key_file)
        if not self.api_key:
            raise ValueError("API key is empty or not read correctly.")
        self.base_url = "https://rest.fnar.net"
        self.headers = {
            "accept": "application/json",
            "Authorization": self.api_key.strip()  # Just the API key, no Bearer prefix
        }
        self.cache_dir = './cache'
        os.makedirs(self.cache_dir, exist_ok=True)

    def _read_api_key(self, api_key_file):
        try:
            with open(api_key_file, 'r') as file:
                return file.read().strip()
        except Exception as e:
            print(f"Error reading API key: {e}")
            return None

    def request(self, method, endpoint, data=None, response_format='json', cache=0, message=None):
        endpoint = self._strip_base_url(endpoint)
        self._validate_url(endpoint)

        url = f"{self.base_url}{endpoint}"
        cache_filename = self._generate_cache_filename(url, method, data)
        cache_path = os.path.join(self.cache_dir, cache_filename)

        # Handle cache loading
        if os.path.exists(cache_path):
            if cache == 0 or cache == False or str(cache).lower() == 'never':
                pass
            elif cache == -1 or cache == True or str(cache).lower() == 'always' or str(cache).lower() == 'forever':
                return self._load_cached_file(cache_path, response_format)
            elif cache >= 0:
                cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))
                if cache_age.total_seconds() < cache:
                    return self._load_cached_file(cache_path, response_format)

        # Fetch the data from the API

        if type(message) is str:
            print(message)
        elif message is not None:
            print(f"Fetching {url}...")

        for attempt in range(MAX_RETRIES):
            try:
                if method.upper() == 'GET':
                    response = requests.get(url, headers=self.headers)
                elif method.upper() == 'POST':
                    response = requests.post(url, headers=self.headers, json=data)
                else:
                    raise ValueError("Unsupported HTTP method.")

                response.raise_for_status()  # Raise HTTPError for bad responses

                # Save response to cache if caching is enabled
                if cache != 0:
                    self._save_to_cache(cache_path, response, response_format)

                if response_format == 'json':
                    return response.json()
                elif response_format == 'csv':
                    return self._parse_csv(response.text)
                else:
                    raise ValueError("Unsupported response format.")

            except requests.exceptions.RequestException as e:
                if response.status_code == 522 and attempt < MAX_RETRIES - 1:
                    print(f"Fetching {endpoint} attempt {attempt + 1}/{MAX_RETRIES} failed with a 522 error. Retrying...")
                else:
                    raise Exception(f"Failed to fetch data: {str(e)}")

    def _generate_cache_filename(self, url, method, data):
        """Generate a human-readable cache filename based on the request."""
        parsed_url = urlparse(url)
        # Use the path, method, and query parameters to create the filename
        filename_parts = [
            method.upper(),
            re.sub(r'\W+', '_', parsed_url.path.strip('/')),
            urlencode(data) if data else ''
        ]
        # Join all parts, remove any trailing underscores, and add a .json or .csv extension
        filename = '_'.join(filter(None, filename_parts)).strip('_')
        extension = 'json' if 'json' in self.headers['accept'] else 'csv'
        filename = f"{filename}.{extension}"
        return quote_plus(filename)  # Ensure the filename is safe for filesystems

    def _load_cached_file(self, cache_path, response_format):
        """Load the cached file and return its contents."""
        with open(cache_path, 'r') as cache_file:
            if response_format == 'json':
                return json.load(cache_file)
            elif response_format == 'csv':
                return self._parse_csv(cache_file.read())
            else:
                raise ValueError("Unsupported response format.")

    def _save_to_cache(self, cache_path, response, response_format):
        """Save the API response to a cache file."""
        with open(cache_path, 'w') as cache_file:
            if response_format == 'json':
                json.dump(response.json(), cache_file, indent=2)
            elif response_format == 'csv':
                cache_file.write(response.text)
            else:
                raise ValueError("Unsupported response format.")

    def _strip_base_url(self, endpoint):
        return re.sub(r"https?://[^/]+", "", endpoint)

    def _validate_url(self, endpoint):
        # Basic validation: ensure no malformed characters are present, e.g., accidental quotes
        if re.search(r"['\"<>]", endpoint):
            raise ValueError(f"Malformed URL detected: {endpoint}")

    def _parse_csv(self, csv_text):
        # Use pandas to read the CSV text
        df = pd.read_csv(StringIO(csv_text))
        # Convert DataFrame to list of dictionaries
        return df.to_dict(orient='records')

# Simplify usage: Auto-initialize FIOAPI instance
fio = FIOAPI()

# Example usage
if __name__ == "__main__":
    username = "fishmodem"
    planet_id = "7f1135f5d7792a058c8be66e7cbcb536"

    try:
        # Example GET request with caching for 300 seconds
        production_data = fio.request("GET", f"/production/{username}", cache=0)
        print(json.dumps(production_data, indent=2))

        # Example CSV request with caching disabled
        all_planets_data = fio.request("GET", "/csv/planets", response_format="csv", cache=60*60*24)
        print(all_planets_data)
    except Exception as e:
        print(f"An error occurred: {e}")
