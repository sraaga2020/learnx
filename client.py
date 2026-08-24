import os
from dotenv import load_dotenv
from openai import OpenAI

# Force fresh environment variables loading from your local .env file
load_dotenv(override=True)

# Fetch the Groq API key
api_key = os.getenv("GROQ_API_KEY")

# Initialize the standard client, pointing it to Groq's endpoint
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key
)

# Groq retires model IDs periodically, so we never hardcode a single one.
# Preference order: best quality first, cheap/fast fallbacks last.
PREFERRED_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "moonshotai/kimi-k2-instruct",
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

_resolved_model = None


def _available_models():
    """Ask Groq which models this API key can actually use."""
    try:
        return {m.id for m in client.models.list().data}
    except Exception:
        return set()


def resolve_model(force: bool = False) -> str:
    """Pick the best model this key has access to, then cache it."""
    global _resolved_model
    if _resolved_model and not force:
        return _resolved_model

    # Explicit override wins if set in .env / hosting env vars.
    override = os.getenv("GROQ_MODEL")
    if override:
        _resolved_model = override
        return _resolved_model

    available = _available_models()
    if available:
        for candidate in PREFERRED_MODELS:
            if candidate in available:
                _resolved_model = candidate
                return _resolved_model
        # Nothing from our list: fall back to any non-audio/vision chat model.
        chat_models = sorted(
            m for m in available
            if not any(x in m.lower() for x in ("whisper", "tts", "guard", "embed"))
        )
        if chat_models:
            _resolved_model = chat_models[0]
            return _resolved_model

    # Could not list models (network/permissions) - use first preference.
    _resolved_model = PREFERRED_MODELS[0]
    return _resolved_model


def gem3(prompt: str) -> str:
    """
    Unified communication wrapper for Career Granny.
    Routes queries to the best chat model available on Groq for this API key.
    """
    if not api_key:
        return "Groq API Error: GROQ_API_KEY is not set."

    model = resolve_model()
    tried = []

    while True:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            return response.choices[0].message.content
        except Exception as e:
            message = str(e)
            tried.append(model)

            # Model gone or not permitted -> re-resolve and retry with another.
            if ("model_not_found" in message or "does not exist" in message
                    or "decommissioned" in message) and len(tried) < 4:
                available = _available_models()
                next_model = None
                for candidate in PREFERRED_MODELS:
                    if candidate in tried:
                        continue
                    if not available or candidate in available:
                        next_model = candidate
                        break
                if next_model:
                    globals()["_resolved_model"] = next_model
                    model = next_model
                    continue

            return f"Groq API Error: {message}"
