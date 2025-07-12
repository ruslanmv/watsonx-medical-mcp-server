# test/test_local.py

"""
Slow integration tests that hit the real IBM watsonx.ai endpoint.

To run them locally or on CI you MUST set in your `.env` at project root:

    WATSONX_APIKEY=<your-api-key>
    PROJECT_ID=<your-project-uuid>
    RUN_WATSONX_LIVE_TESTS=true

Optionally:
    WATSONX_URL=<your-service-url>         # e.g. https://us-south.ml.cloud.ibm.com
    MODEL_ID=<your-model-id>               # e.g. meta-llama/llama-3-2-90b-vision-instruct
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import pytest

# Load .env from project root
load_dotenv()

# ---------------------------------------------------------------------------
# Decide whether to run live tests
# ---------------------------------------------------------------------------
REQUIRED_VARS = ("WATSONX_APIKEY", "PROJECT_ID")
creds_present = all(os.getenv(v) for v in REQUIRED_VARS)
opted_in = os.getenv("RUN_WATSONX_LIVE_TESTS", "false").lower() == "true"

if __name__ != "__main__":
    # Under pytest: skip entire module if not both opted-in AND creds present
    if not (creds_present and opted_in):
        pytest.skip(
            "Live watsonx tests skipped – set RUN_WATSONX_LIVE_TESTS=true "
            "and provide WATSONX_APIKEY and PROJECT_ID in .env",
            allow_module_level=True,
        )
else:
    # Direct `python test_local.py`: friendly message and exit if skipping
    if not (creds_present and opted_in):
        print(
            "Live watsonx tests skipped – set RUN_WATSONX_LIVE_TESTS=true "
            "and provide WATSONX_APIKEY and PROJECT_ID in .env"
        )
        sys.exit(0)

# ---------------------------------------------------------------------------
# Now safe to import and run against the real server
# ---------------------------------------------------------------------------
os.environ.setdefault("WATSONX_MODE", "live")

# Ensure we import server.py from project root
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
    # Credentials present & opted-in → run pytest on this file
    sys.exit(pytest.main([__file__]))
