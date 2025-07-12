# test/test_server.py

import sys
from pathlib import Path
import os
import pytest
from unittest.mock import patch, MagicMock

# --- Setup ---

# 1. Add the project root to the Python path to allow imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 2. Set dummy environment variables BEFORE importing the server.
# This is crucial to prevent 'server.py' from raising an error on import
# because it can't find the required variables.
os.environ['WATSONX_APIKEY'] = 'dummy_api_key_for_testing'
os.environ['PROJECT_ID'] = 'dummy_project_id_for_testing'

# 3. Now it's safe to import the server module
import server

# --- Tests ---

# The @patch decorator intercepts calls to create a ModelInference instance
# and replaces it with our mock object for the duration of the test.
@patch('server.ModelInference')
def test_chat_with_watsonx_success(mock_model_inference):
    """
    GIVEN a user query
    WHEN the 'chat_with_watsonx' tool is called
    THEN it should return a mocked successful response from the API
    """
    # Arrange: Configure the mock to simulate a successful API call
    mock_api_client = MagicMock()
    mock_api_client.generate_text.return_value = {
        "results": [{"generated_text": "This is a successful mock response."}]
    }
    mock_model_inference.return_value = mock_api_client

    # Act: Call the function we want to test
    query = "What is a mock test?"
    response = server.chat_with_watsonx(query)

    # Assert: Check that the function returned the expected text
    assert response == "This is a successful mock response."
    mock_api_client.generate_text.assert_called_once()


@patch('server.ModelInference')
def test_chat_with_watsonx_api_error(mock_model_inference):
    """
    GIVEN a user query
    WHEN the Watsonx API call fails
    THEN the 'chat_with_watsonx' tool should handle the error gracefully
    """
    # Arrange: Configure the mock to raise an error when called
    mock_api_client = MagicMock()
    mock_api_client.generate_text.side_effect = Exception("API Connection Failed")
    mock_model_inference.return_value = mock_api_client

    # Act: Call the function
    query = "This query will trigger a failure."
    response = server.chat_with_watsonx(query)

    # Assert: Check that our error handling logic returned the correct message
    assert "Error generating response: API Connection Failed" in response

def test_get_server_info_resource():
    """
    GIVEN the server is running
    WHEN the 'get_server_info' resource is requested
    THEN it should return a non-empty string containing server details
    """
    # Act
    info_string = server.get_server_info()

    # Assert
    assert isinstance(info_string, str)
    assert server.SERVER_NAME in info_string
    assert "Available Tools:" in info_string