import os
import time
import mimetypes
import httpx
from pathlib import Path
from typing import Optional, Union
from google import genai
from google.genai import types

PRIMARY_MODEL = "gemma-4-31b-it"
FALLBACK_MODEL = "gemma-4-26b-a4b-it"

class ModelNotFoundError(Exception):
    """Raised when a requested model is not found on the Gemini/Gemma API."""
    pass

def load_env():
    """Load GEMINI_API_KEY or GOOGLE_API_KEY from .env files if not already set."""
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return
    for env_path in [Path.cwd() / ".env", Path.home() / ".env"]:
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("'\"")
                        if k in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                            os.environ[k] = v
            except Exception:
                pass

def get_client() -> genai.Client:
    load_env()
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please set GEMINI_API_KEY in your environment or in a .env file."
        )
    # Use verify=False to prevent SSL certificate errors on Windows environment, with 30s timeout
    http_opts = types.HttpOptions(
        httpx_client=httpx.Client(verify=False, timeout=30.0)
    )
    return genai.Client(api_key=api_key, http_options=http_opts)

def ask(
    prompt: str,
    image_path: Optional[Union[str, Path]] = None,
    temperature: float = 0.7,
    max_retries: int = 1
) -> str:
    """
    Sends a prompt (and optional image) to Gemma models using the google-genai SDK.
    Uses max 1 retry per API request for speed and reliability during evaluation.
    """
    client = get_client()
    contents = []

    if image_path:
        img_p = Path(image_path)
        if not img_p.exists():
            raise FileNotFoundError(f"Image not found at path: {image_path}")
        
        mime_type, _ = mimetypes.guess_type(img_p)
        if not mime_type:
            ext = img_p.suffix.lower()
            if ext in ('.png', '.apng'):
                mime_type = 'image/png'
            elif ext in ('.jpg', '.jpeg'):
                mime_type = 'image/jpeg'
            elif ext == '.webp':
                mime_type = 'image/webp'
            else:
                mime_type = 'image/png'
        
        with open(img_p, 'rb') as f:
            img_bytes = f.read()
        
        image_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
        contents.append(image_part)

    contents.append(prompt)
    config = types.GenerateContentConfig(temperature=temperature)

    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL]
    last_exception = None

    for model_name in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config
                )

                if response and response.text and response.text.strip():
                    return response.text.strip()
                
                # Empty response retry
                time.sleep(1.0)
                continue

            except Exception as e:
                err_str = str(e)
                last_exception = e

                # Check if model is not found
                if "NOT_FOUND" in err_str.upper() or "404" in err_str or "not found" in err_str.lower():
                    break  # Try fallback model

                # Transient error: retry max 1 time after 1 second delay
                if attempt < max_retries:
                    time.sleep(1.0)
                    continue
                else:
                    raise e

    if last_exception and ("NOT_FOUND" in str(last_exception).upper() or "404" in str(last_exception) or "not found" in str(last_exception).lower()):
        raise ModelNotFoundError(f"Requested Gemma models ({PRIMARY_MODEL}, {FALLBACK_MODEL}) returned 'not found': {last_exception}")

    raise RuntimeError(f"Failed API call for models {models_to_try}: {last_exception}")

if __name__ == "__main__":
    print("Testing llm.py...")
    try:
        res = ask("Say 'Hello from Gemma 4!'")
        print("Response:", res)
    except Exception as ex:
        print("Test error:", type(ex).__name__, ex)
