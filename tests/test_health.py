def test_health_endpoint(client):
    """
    Test the /health endpoint returns 200 OK and status: ok
    """
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
