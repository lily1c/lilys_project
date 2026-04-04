import pytest
import json

def test_shorten_url(client):
    """
    Test that shortening a URL returns a 201 status and a short_code
    """
    payload = {
        "original_url": "https://example.com/test-unit",
        "title": "Unit Test URL"
    }
    response = client.post('/urls', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 201
    
    data = response.get_json()
    assert 'short_code' in data
    assert data['original_url'] == "https://example.com/test-unit"

def test_shorten_url_invalid_format(client):
    """
    The Unwitting Stranger: Test that malformed URLs are rejected
    """
    payload = {
        "original_url": "google",
        "title": "Invalid URL"
    }
    response = client.post('/urls', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    assert "error" in response.get_json()
