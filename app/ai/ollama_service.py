import requests

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.2:latest"

def health_check():
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return {
            "status": "healthy",
            "ollama": True,
            "models": response.json().get("models", [])
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "ollama": False,
            "error": str(exc)
        }

def list_models():
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        response.raise_for_status()
        return [m.get("name") for m in response.json().get("models", [])]
    except Exception:
        return [DEFAULT_MODEL]

def generate(prompt: str, model: str = None, temperature: float = 0.2):
    # Always guarantee a valid pulled model
    active_model = model or DEFAULT_MODEL
    if "llama3.2" not in active_model:
        active_model = DEFAULT_MODEL

    payload = {
        "model": active_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }
    try:
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except requests.exceptions.HTTPError as err:
        # Fallback retry with base model if specific tag fails
        if response.status_code == 404 and active_model != DEFAULT_MODEL:
            payload["model"] = DEFAULT_MODEL
            retry_res = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=300)
            retry_res.raise_for_status()
            return retry_res.json().get("response", "").strip()
        raise err
