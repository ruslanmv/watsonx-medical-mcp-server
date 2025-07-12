# test/test_server.py
import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Setup project path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set environment variables before importing server
os.environ['WATSONX_APIKEY'] = 'dummy_api_key_for_testing'
os.environ['PROJECT_ID'] = 'dummy_project_id_for_testing'

# Import server after setting environment variables
import server


class TestWatsonxMCPServer:
    """Test suite for Watsonx Medical MCP Server"""

    @patch('server.ModelInference')
    def test_chat_with_watsonx_success(self, mock_model_inference):
        """Test successful chat response"""
        # Arrange
        mock_api_client = MagicMock()
        mock_api_client.generate_text.return_value = {
            "results": [{"generated_text": "Test response from watsonx"}]
        }
        mock_model_inference.return_value = mock_api_client

        # Act
        response = server.chat_with_watsonx("What is a test?")

        # Assert
        assert response == "Test response from watsonx"
        mock_api_client.generate_text.assert_called_once()

    @patch('server.ModelInference')
    def test_chat_with_watsonx_api_error(self, mock_model_inference):
        """Test error handling in chat function"""
        # Arrange
        mock_api_client = MagicMock()
        mock_api_client.generate_text.side_effect = Exception("API Error")
        mock_model_inference.return_value = mock_api_client

        # Act
        response = server.chat_with_watsonx("This will fail")

        # Assert
        assert "Error generating response: API Error" in response

    @patch('server.ModelInference')
    def test_analyze_medical_symptoms(self, mock_model_inference):
        """Test medical symptom analysis"""
        # Arrange
        mock_api_client = MagicMock()
        mock_api_client.generate_text.return_value = {
            "results": [{"generated_text": "Medical analysis result"}]
        }
        mock_model_inference.return_value = mock_api_client

        # Act
        response = server.analyze_medical_symptoms(
            "headache and fever", 
            patient_age=30, 
            patient_gender="female"
        )

        # Assert
        assert response == "Medical analysis result"
        mock_api_client.generate_text.assert_called_once()

    def test_get_server_info_resource(self):
        """Test server info resource"""
        # Act
        info = server.get_server_info()

        # Assert
        assert isinstance(info, str)
        assert server.SERVER_NAME in info
        assert "Available Tools:" in info

    def test_clear_conversation_history(self):
        """Test conversation history clearing"""
        # Arrange - add some history first
        server.conversation_history.append({"role": "user", "content": "test"})
        
        # Act
        result = server.clear_conversation_history()
        
        # Assert
        assert len(server.conversation_history) == 0
        assert "cleared" in result.lower()

    def test_get_patient_greeting(self):
        """Test patient greeting resource"""
        # Act
        greeting = server.get_patient_greeting("John")
        
        # Assert
        assert "John" in greeting
        assert "medical assistant" in greeting.lower()

    def test_medical_consultation_prompt(self):
        """Test medical consultation prompt generation"""
        # Act
        prompt = server.medical_consultation_prompt(
            "headache", 
            duration="2 days", 
            severity="moderate"
        )
        
        # Assert
        assert "headache" in prompt
        assert "2 days" in prompt
        assert "moderate" in prompt
        assert "medical assistant" in prompt.lower()

    def test_health_education_prompt(self):
        """Test health education prompt generation"""
        # Act
        prompt = server.health_education_prompt("diabetes")
        
        # Assert
        assert "diabetes" in prompt
        assert "health educator" in prompt.lower()
        assert "prevention" in prompt.lower()