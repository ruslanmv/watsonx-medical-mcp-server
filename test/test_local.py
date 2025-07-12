# test/test_local.py
"""
Slow integration tests that hit the real IBM watsonx.ai endpoint.

To run them locally or on CI you MUST set:

    export WATSONX_APIKEY=<secret>
    export PROJECT_ID=<your-project-uuid>
    export RUN_WATSONX_LIVE_TESTS=true         # opt-in flag
    # optional:
    # export WATSONX_URL=https://us-south.ml.cloud.ibm.com
"""

import os
import pytest
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Skip automatically when credentials / opt-in flag are missing
# ---------------------------------------------------------------------------
REQUIRED_VARS = ("WATSONX_APIKEY", "PROJECT_ID")
if (
    not all(os.getenv(v) for v in REQUIRED_VARS)
    or os.getenv("RUN_WATSONX_LIVE_TESTS", "false").lower() != "true"
):
    pytest.skip(
        "Live watsonx tests skipped – set RUN_WATSONX_LIVE_TESTS=true and "
        "provide credentials to enable.",
        allow_module_level=True,
    )

# ---------------------------------------------------------------------------
# Ensure live mode before importing the server
# ---------------------------------------------------------------------------
os.environ.setdefault("WATSONX_MODE", "live")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import server  # noqa: E402


@pytest.mark.integration
def test_live_chat_with_watsonx():
    prompt = (
        "In one short sentence, explain why good sleep hygiene is important for health."
    )
    response = server.chat_with_watsonx(prompt, max_tokens=60, temperature=0.2)

    assert isinstance(response, str)
    assert response  # non-empty
    assert "Error generating response" not in response


@pytest.mark.integration
def test_live_analyze_medical_symptoms():
    response = server.analyze_medical_symptoms(
        "dry cough and mild fever", patient_age=25, patient_gender="male"
    )

    assert isinstance(response, str)
    assert response
    assert "Possible causes" in response or "possible causes" in response
