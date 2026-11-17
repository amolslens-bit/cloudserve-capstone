"""Shows how many free OpenRouter requests are left today. Never prints the key."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
r = requests.get("https://openrouter.ai/api/v1/key",
                 headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"}, timeout=15)
d = r.json().get("data", {})
print("Free requests today:", d.get("free_model_daily_requests"))
print("Has bought credits before:", not d.get("is_free_tier", True))
