import os
import requests

API_KEY = "YOUR_API_KEY"
headers = {"Authorization": f"Bearer {API_KEY}"}
url = "https://api.groq.com/openai/v1/models"
try:
    response = requests.get(url, headers=headers)
    data = response.json()
    for m in data.get('data', []):
        print(m['id'])
except Exception as e:
    print("Error:", e)
