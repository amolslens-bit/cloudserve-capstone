import os, requests
from dotenv import load_dotenv
load_dotenv()

tests = {
    "OpenRouter": ("https://openrouter.ai/api/v1/chat/completions",
                   os.environ["OPENROUTER_API_KEY"], os.environ["MODEL_NAME"]),
    "Groq": ("https://api.groq.com/openai/v1/chat/completions",
             os.environ["GROQ_API_KEY"], os.environ["GROQ_MODEL"]),
}
for name, (url, key, model) in tests.items():
    r = requests.post(url, headers={"Authorization": f"Bearer {key.strip()}"},
                      json={"model": model, "messages": [{"role": "user", "content": "Reply with the word ready."}]},
                      timeout=30)
    print(name, r.status_code, r.json().get("choices", [{}])[0].get("message", {}).get("content", r.text[:200]))