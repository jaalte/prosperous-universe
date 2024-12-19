#!/usr/bin/env python3

import requests
import json
import pandas as pd
import re
import os
from io import StringIO
from urllib.parse import urlencode, urlparse, quote_plus
from datetime import datetime, timedelta
import time
from collections import deque

MAX_RETRIES = 3
REQUESTS_PER_RATE_LIMIT = 1
RATE_LIMIT = 0.5  # seconds

API_KEY_FILE = './apikey.txt'

class FIOAPI:
    def __init__(self):
        self.api_key = self._get_api_key()
        #if not self.api_key:
        #    raise ValueError("API key is empty or not read correctly.")
        self.base_url = "https://rest.fnar.net"
        self.headers = {
            "accept": "application/json",
        }
        if self.api_key:
            self.headers['Authorization'] = self.api_key.strip() # Just the API key, no Bearer prefix

        self.cache_dir = './cache'
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize a deque to keep track of request timestamps
        self.request_times = deque()

    # Special function to load, prompt, and cache API key
    def _get_api_key(self):
        # If it exists
        if os.path.exists('./apikey.txt'):
            with open('./apikey.txt', 'r') as f:
                api_key = f.read().strip()
                if api_key:
                    return api_key
                else:
                    pass # Remake file as below

        # If it doesn't exist
        api_key = input("Enter your API key: ")
        with open('./apikey.txt', 'w') as f:
            f.write(api_key)
        print(f"Saved API key to ./apikey.txt. Delete it if you want to reset it.")

        return api_key

    def request(self, method, endpoint, data=None, response_format=None, cache=0, message=None):
        endpoint = self._strip_base_url(endpoint)
        self._validate_url(endpoint)

        # Automatically set response_format to 'csv' if the endpoint starts with 'csv'
        if response_format is None:
            response_format = 'csv' if endpoint.strip('/').split('/')[0] == 'csv' else 'json'

        url = f"{self.base_url}{endpoint}"
        cache_filename = self._generate_cache_filename(url, method, data, response_format)
        cache_path = os.path.join(self.cache_dir, cache_filename)

        # Check if the response is cached, skip rate limiting if cache is being used
        if os.path.exists(cache_path):
            if cache == 0 or cache == False or str(cache).lower() == 'never':
                pass
            elif cache == -1 or cache == True or str(cache).lower() == 'always' or str(cache).lower() == 'forever':
                return self._load_cached_file(cache_path, response_format)
            elif cache >= 0:
                cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))
                if cache_age.total_seconds() < cache:
                    return self._load_cached_file(cache_path, response_format)

        # Apply rate limiting only if the request is not served from cache
        current_time = time.time()

        # Remove timestamps that are outside of the RATE_LIMIT window
        while self.request_times and current_time - self.request_times[0] > RATE_LIMIT:
            self.request_times.popleft()

        # If the number of requests in the last RATE_LIMIT seconds exceeds the allowed limit, delay the request
        if len(self.request_times) >= REQUESTS_PER_RATE_LIMIT:
            time_to_wait = RATE_LIMIT - (current_time - self.request_times[0])
            if time_to_wait > 0:
                time.sleep(time_to_wait)

        # Record the time of this request
        self.request_times.append(time.time())

        # Make a web request
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

                response.raise_for_status()

                # Check if response is empty
                if not response.text.strip():  # Empty response body
                    raise Exception(f"Empty response from {url}. No data returned by the server.")

                # Save response to cache if caching is enabled
                if cache != 0:
                    self._save_to_cache(cache_path, response, response_format)

                # Try to encode the response in the requested format
                try:
                    if response_format == 'json':
                        return response.json()
                    elif response_format == 'csv':
                        df = pd.read_csv(StringIO(response.text))
                        return df.to_dict(orient='records')
                    else:
                        raise ValueError("Unsupported response format.")
                except:
                    raise Exception(f"Failed to parse response: {response.text}")

            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"Fetching {endpoint} attempt {attempt + 1}/{MAX_RETRIES} failed. Retrying...")
                else:
                    raise Exception(f"Failed to fetch data: {str(e)}")


    def _generate_cache_filename(self, url, method, data, response_format):
        """Generate a human-readable cache filename based on the request."""
        parsed_url = urlparse(url)
        # Use the path, method, and query parameters to create the filename
        filename_parts = [
            method.upper(),
            re.sub(r'\W+', '_', parsed_url.path.strip('/')),
            urlencode(data) if data else ''
        ]
        # Join all parts, remove any trailing underscores, and add the correct extension
        filename = '_'.join(filter(None, filename_parts)).strip('_')
        extension = 'json' if response_format == 'json' else 'csv'
        filename = f"{filename}.{extension}"
        return quote_plus(filename)  # Ensure the filename is safe for filesystems

    def _load_cached_file(self, cache_path, response_format):
        """Load the cached file and return its contents."""
        with open(cache_path, 'r') as cache_file:
            if response_format == 'json':
                return json.load(cache_file)
            elif response_format == 'csv':
                df = pd.read_csv(StringIO(cache_file.read()))
                return df.to_dict(orient='records')
            else:
                raise ValueError("Unsupported response format.")

    def _save_to_cache(self, cache_path, response, response_format):
        """Save the API response to a cache file."""
        # Check if the response is empty
        if response_format == 'json' and not response.json():
            return
        elif response_format == 'csv' and not response.text.strip():
            return

        # Save the response to the cache
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

# Simplify usage: Auto-initialize FIOAPI instance
fio = FIOAPI()
