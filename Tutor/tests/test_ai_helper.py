import pytest
from unittest.mock import patch, MagicMock
from ai_helper import generate_study_guide, get_openai_client

@patch('ai_helper.get_openai_client')
def test_generate_study_guide_success(mock_get_client):
    """Test successful study guide generation via the DeepSeek API."""
    # Create a mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "===== TEST CONTENT =====\nThis is a test study guide."
    
    # Set up the mock client
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_client.return_value = mock_client
    
    # Test data
    test_data = {
        'class': 'Mathematics',
        'unit': 'Calculus',
        'year': 'University',
        'details': 'Derivatives and integrals'
    }
    
    # Call the function
    content, error = generate_study_guide(test_data)
    
    # Verify results
    assert error is None
    assert "===== TEST CONTENT =====" in content
    assert "This is a test study guide." in content
    
    # Verify the API was called with correct parameters
    mock_client.chat.completions.create.assert_called_once()
    args, kwargs = mock_client.chat.completions.create.call_args
    
    # Check model
    assert kwargs['model'] == "deepseek-chat"
    
    # Check that messages contain our test data
    messages = kwargs['messages']
    user_message = [m for m in messages if m['role'] == 'user'][0]['content']
    assert 'University' in user_message
    assert 'Mathematics' in user_message
    assert 'Calculus' in user_message
    assert 'Derivatives and integrals' in user_message

@patch('ai_helper.get_openai_client')
def test_generate_study_guide_without_section_headers(mock_get_client):
    """Test study guide generation where the API doesn't return proper section headers."""
    # Create a mock response without section headers
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is a test study guide without proper section headers."
    
    # Set up the mock client
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_client.return_value = mock_client
    
    # Test data
    test_data = {
        'class': 'Literature',
        'unit': 'Shakespeare',
        'year': 'High School',
        'details': 'Romeo and Juliet'
    }
    
    # Call the function
    content, error = generate_study_guide(test_data)
    
    # Verify results
    assert error is None
    assert "===== STUDY GUIDE FOR LITERATURE - SHAKESPEARE =====" in content
    assert "This is a test study guide without proper section headers." in content

@patch('ai_helper.get_openai_client')
def test_generate_study_guide_failure(mock_get_client):
    """Test study guide generation with API failure."""
    # Set up the mock client to raise an exception
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API connection error")
    mock_get_client.return_value = mock_client
    
    # Test data
    test_data = {
        'class': 'Computer Science',
        'unit': 'Algorithms',
        'year': 'Graduate',
        'details': 'Sorting algorithms'
    }
    
    # Call the function
    content, error = generate_study_guide(test_data)
    
    # Verify results
    assert content is None
    assert error is not None
    assert "Error generating study guide" in error
    assert "API connection error" in error