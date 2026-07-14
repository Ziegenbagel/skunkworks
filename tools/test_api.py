import os

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("VON_NEUMANN_API_KEY")
base_url = os.getenv(
    "VON_NEUMANN_BASE_URL",
    "https://neumann-probe.net",
)

print(f"Base URL: {base_url}")
print(f"API key loaded: {api_key is not None}")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json",
}

print("Sending request...")

response = requests.get(
    f"{base_url}/api/me",
    headers=headers,
    timeout=30,
)

print(f"Status Code: {response.status_code}")
print(response.text)