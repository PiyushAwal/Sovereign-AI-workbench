from app.ai.ollama_service import list_models

DEFAULT_MODEL = "llama3.2:latest"

def select_model():
    """
    Select an available local Ollama model.
    Priority:
    1. llama3.2
    2. first available local model
    """
    try:
        models = list_models()
        available = []
        for item in models:
            if isinstance(item, dict):
                name = item.get("name")
                if name:
                    available.append(name)

        for name in available:
            if name.startswith("llama3.2"):
                return name

        if available:
            return available[0]
    except Exception:
        pass

    return DEFAULT_MODEL
