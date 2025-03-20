import pytest
import os
import json
from unittest.mock import patch, MagicMock
from app import app
from study_guide import generate_pdf, mock_deekseek_api

@pytest.fixture
def client():
    """Create a test client for the app."""
    app.config['TESTING'] = True
    # Create test directories
    os.makedirs("static/guides", exist_ok=True)
    with app.test_client() as client:
        yield client
    
    # Clean up test files
    for file in os.listdir("static/guides"):
        if file.startswith("study_guide_test_"):
            os.remove(os.path.join("static/guides", file))

def test_mock_deekseek_api():
    """Test the mock API function."""
    test_data = {
        'class': 'Biology',
        'unit': 'Cell Structure',
        'year': 'High School',
        'details': 'Focus on cell organelles'
    }
    
    result = mock_deekseek_api(test_data)
    
    assert 'STUDY GUIDE FOR BIOLOGY - CELL STRUCTURE' in result
    assert 'Year Level: High School' in result
    assert 'Focus on cell organelles' in result
    assert '===== KEY CONCEPTS =====' in result

def test_generate_pdf():
    """Test PDF generation."""
    test_content = """===== TEST SECTION =====
This is test content.
- Bullet point 1
- Bullet point 2
   - Sub bullet point
"""
    output_path = "static/guides/study_guide_test_pdf.pdf"
    
    generate_pdf(test_content, output_path, "Test Title", "Test Level")
    
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0

@patch('study_guide.generate_study_guide')
def test_generate_study_guide_endpoint_success(mock_generate, client):
    """Test the study guide generation endpoint with successful generation."""
    # Mock the generate_study_guide function
    mock_generate.return_value = ("===== TEST STUDY GUIDE =====\nTest content", None)
    
    # Test data
    test_data = {
        'class': 'Physics',
        'unit': 'Mechanics',
        'year': 'College',
        'details': 'Newton\'s laws'
    }
    
    # Make request
    response = client.post('/generate-study-guide', 
                          data=json.dumps(test_data),
                          content_type='application/json')
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'filename' in data
    assert data['filename'].endswith('.pdf')
    assert 'content' in data
    # Just check for any content, as the format might vary
    assert len(data['content']) > 0

@patch('study_guide.generate_study_guide')
def test_generate_study_guide_endpoint_failure(mock_generate, client):
    """Test the study guide generation endpoint with an error."""
    # Temporarily set the environment to not use the mock API for this test
    import os
    original_use_mock = os.environ.get('USE_MOCK_API', 'True')
    os.environ['USE_MOCK_API'] = 'False'
    
    try:
        # Mock the generate_study_guide function to return an error
        mock_generate.return_value = (None, "API error")
        
        # Test data
        test_data = {
            'class': 'Chemistry',
            'unit': 'Organic',
            'year': 'College',
            'details': 'Test details'
        }
        
        # Make request
        response = client.post('/generate-study-guide', 
                            data=json.dumps(test_data),
                            content_type='application/json')
        
        # Check response
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'error' in data
        assert 'API error' in data['error']
    finally:
        # Restore the original environment variable
        os.environ['USE_MOCK_API'] = original_use_mock

def test_download_endpoint(client):
    """Test the download endpoint."""
    # Create a test file
    test_file_path = "static/guides/study_guide_test_download.txt"
    with open(test_file_path, "w") as f:
        f.write("Test content for download")
    
    # Test valid download
    response = client.get('/download/study_guide_test_download.txt')
    assert response.status_code == 200
    # Check that the Content-Type starts with text/plain, ignoring charset details
    assert response.headers["Content-Type"].startswith("text/plain")
    assert response.headers["Content-Disposition"].startswith("attachment")
    
    # Test file not found
    response = client.get('/download/non_existent_file.txt')
    assert response.status_code == 404
    
    # Test path traversal attempt
    response = client.get('/download/../../../etc/passwd')
    assert response.status_code == 404
    
    # Clean up
    os.remove(test_file_path)