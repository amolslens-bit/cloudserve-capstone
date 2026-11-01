import os, requests
from dotenv import load_dotenv, dotenv_values

load_dotenv()
print("Variables in .env:", list(dotenv_values().keys()))

r = requests.get("https://api.groq.com/openai/v1/models",
                 headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"].strip()},
                 timeout=30)
print(r.status_code)
print([m["id"] for m in r.json().get("data", [])])