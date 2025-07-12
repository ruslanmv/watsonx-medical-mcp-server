# test/test_local.py

"""
Slow integration tests that hit the real IBM watsonx.ai endpoint.

To run them locally or on CI you MUST have a `.env` file at your project root containing:

    WATSONX_APIKEY=<your-api-key>
    PROJECT_ID=<your-project-uuid>
    # Optional (will fall back to defaults if omitted):
    # WATSONX_URL=<your-service-url>           # e.g. https://us-south.ml.cloud.ibm.com
    # MODEL_ID=<your-model-id>                  # e.g. meta-llama/llama-3-2-90b-vision-instruct
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import pytest

# Load .env from project root
load_dotenv()

# ---------------------------------------------------------------------------
# Only require API key and project ID; URL and MODEL_ID will use defaults
# ---------------------------------------------------------------------------
REQUIRED_VARS = ("WATSONX_APIKEY", "PROJECT_ID")
missing_creds = not all(os.getenv(v) for v in REQUIRED_VARS)

if __name__ != "__main__":
    # Running under pytest → skip tests if creds missing
    if missing_creds:
        pytest.skip(
            "Live watsonx tests skipped – please set WATSONX_APIKEY and PROJECT_ID in .env",
            allow_module_level=True,
        )
else:
    # Direct `python test_local.py` → print message and exit if creds missing
    if missing_creds:
        print(
            "Live watsonx tests skipped – please set WATSONX_APIKEY and PROJECT_ID in .env"
        )
        sys.exit(0)

# ---------------------------------------------------------------------------
# Ensure live mode before importing the server
# ---------------------------------------------------------------------------
os.environ.setdefault("WATSONX_MODE", "live")

# Make sure we import server.py from the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import server  # noqa: E402


def test_live_chat_with_watsonx():
    prompt = (
        "In one short sentence, explain why good sleep hygiene is important for health."
    )
    response = server.chat_with_watsonx(
        prompt,
        max_tokens=60,
        temperature=0.2,
    )

    assert isinstance(response, str)
    assert response  # non-empty
    assert "Error generating response" not in response


def test_live_analyze_medical_symptoms():
    response = server.analyze_medical_symptoms(
        "dry cough and mild fever",
        patient_age=25,
        patient_gender="male",
    )

    assert isinstance(response, str)
    assert response  # non-empty
    assert "Possible causes" in response or "possible causes" in response


if __name__ == "__main__":
    # Credentials are present → run pytest on this file
    sys.exit(pytest.main([__file__]))
