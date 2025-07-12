# test/test_server.py
import sys
import os
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Boot-strap repository path and force watsonx into mock mode
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["WATSONX_APIKEY"] = "dummy_api_key_for_testing"
os.environ["PROJECT_ID"] = "dummy_project_id_for_testing"
os.environ["WATSONX_MODE"] = "mock"

import server  # noqa: E402


class TestWatsonxMCPServer:
    """Unit-tests for Watsonx Medical MCP Server (offline / mock mode)."""

    # ------------------------------------------------------------------ #
    # chat_with_watsonx
    # ------------------------------------------------------------------ #
    @patch("server.model")
    def test_chat_with_watsonx_success(self, mock_model):
        mock_model.generate_text.return_value = {
            "results": [{"generated_text": "Test response from watsonx"}]
        }

        response = server.chat_with_watsonx("What is a test?")

        assert response == "Test response from watsonx"
        mock_model.generate_text.assert_called_once()

    @patch("server.model")
    def test_chat_with_watsonx_api_error(self, mock_model):
        mock_model.generate_text.side_effect = Exception("API Error")

        response = server.chat_with_watsonx("This will fail")

        assert "Error generating response: API Error" in response
        mock_model.generate_text.assert_called_once()

    # ------------------------------------------------------------------ #
    # analyze_medical_symptoms
    # ------------------------------------------------------------------ #
    @patch("server.model")
    def test_analyze_medical_symptoms(self, mock_model):
        mock_model.generate_text.return_value = {
            "results": [{"generated_text": "Medical analysis result"}]
        }

        response = server.analyze_medical_symptoms(
            "headache and fever", patient_age=30, patient_gender="female"
        )

        assert response == "Medical analysis result"
        mock_model.generate_text.assert_called_once()

    # ------------------------------------------------------------------ #
    # Static helpers & resources
    # ------------------------------------------------------------------ #
    def test_get_server_info_resource(self):
        info = server.get_server_info()

        assert isinstance(info, str)
        assert server.SERVER_NAME in info
        assert "Available Tools:" in info

    def test_clear_conversation_history(self):
        server.conversation_history.append({"role": "user", "content": "test"})
        result = server.clear_conversation_history()

        assert len(server.conversation_history) == 0
        assert "cleared" in result.lower()

    def test_get_patient_greeting(self):
        greeting = server.get_patient_greeting("John")

        assert "John" in greeting
        assert "medical assistant" in greeting.lower()

    def test_medical_consultation_prompt(self):
        prompt = server.medical_consultation_prompt(
            "headache", duration="2 days", severity="moderate"
        )

        assert "headache" in prompt
        assert "2 days" in prompt
        assert "moderate" in prompt
        assert "medical assistant" in prompt.lower()

    def test_health_education_prompt(self):
        prompt = server.health_education_prompt("diabetes")

        assert "diabetes" in prompt
        assert "health educator" in prompt.lower()
        assert "prevention" in prompt.lower()

    # ------------------------------------------------------------------ #
    # get_conversation_summary
    # ------------------------------------------------------------------ #
    @patch("server.model")
    def test_get_conversation_summary_empty(self, mock_model):
        server.conversation_history.clear()
        summary = server.get_conversation_summary()

        assert summary == "No conversation history available."

    @patch("server.model")
    def test_get_conversation_summary_with_history(self, mock_model):
        mock_model.generate_text.return_value = {
            "results": [{"generated_text": "Summary of conversation"}]
        }

        server.conversation_history.clear()
        server.conversation_history.append({"role": "user", "content": "Hello"})
        server.conversation_history.append({"role": "assistant", "content": "Hi there"})

        summary = server.get_conversation_summary()

        assert summary == "Summary of conversation"
        mock_model.generate_text.assert_called_once()

    # ------------------------------------------------------------------ #
    # Configuration sanity
    # ------------------------------------------------------------------ #
    def test_server_configuration(self):
        assert server.SERVER_NAME
        assert server.SERVER_VERSION
        assert server.MODEL_ID
        assert isinstance(server.conversation_history, list)


# (blank line added above to satisfy W292)
