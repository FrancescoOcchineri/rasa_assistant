import requests

try:
    response = requests.post(
        "http://ollama:11434/api/generate",
        json={"model":"mistral", "prompt":"test", "stream":False},
        timeout=120
    )
    response.raise_for_status()
    print(response.json())
except Exception as e:
    print(f"Errore: {e}")
