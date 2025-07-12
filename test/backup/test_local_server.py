# test/test_local_server.py
import sys
from pathlib import Path
import os  # noqa: E402
import server  # noqa: E402

# Setup project path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set environment variables before importing
os.environ['WATSONX_APIKEY'] = 'dummy_api_key_for_testing'
os.environ['PROJECT_ID'] = 'dummy_project_id_for_testing'


def test_server_imports():
    """Test that server module imports correctly"""
    assert hasattr(server, 'mcp')
    assert hasattr(server, 'SERVER_NAME')
    assert hasattr(server, 'conversation_history')


def test_server_name_configuration():
    """Test server name is properly configured"""
    assert server.SERVER_NAME == "Watsonx Medical Assistant"
