import pytest
import os
import sys
import shutil

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup the test environment before all tests."""
    # Create necessary directories
    os.makedirs("static/guides", exist_ok=True)
    
    # Set environment variables for testing
    os.environ["USE_MOCK_API"] = "True"  # Use mock API by default in tests
    os.environ["DEEPSEEK_API_KEY"] = "test_api_key"  # Use test API key
    
    yield
    
    # Clean up test files after all tests
    for file in os.listdir("static/guides"):
        if file.startswith("study_guide_"):
            try:
                os.remove(os.path.join("static/guides", file))
            except:
                pass  # Ignore errors during cleanup