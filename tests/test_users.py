import json

def test_create_user(client):
    """
    Test that creating a user returns a 201 status and the user data
    """
    payload = {
        "username": "test_user_unit",
        "email": "unit@example.com"
    }
    response = client.post('/users', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 201
    
    data = response.get_json()
    assert data['username'] == "test_user_unit"
    assert data['email'] == "unit@example.com"

def test_create_user_too_long(client):
    """
    The Deceitful Scroll: Test that overly long strings are rejected
    """
    payload = {
        "username": "a" * 100, # Max is 50
        "email": "unit@example.com"
    }
    response = client.post('/users', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    assert "error" in response.get_json()
