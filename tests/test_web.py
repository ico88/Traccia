from fastapi.testclient import TestClient
from aulalocale.app import create_app

TOKEN = 'browser-test-token-' * 3
AUTH = {'Authorization': f'Bearer {TOKEN}'}
ORIGIN = {'Origin': 'http://testserver'}


def test_interface_is_self_contained(tmp_path):
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        response = client.get('/')
        assert response.status_code == 200
        assert 'AulaLocale' in response.text
        assert "frame-ancestors 'none'" in response.headers['content-security-policy']
        for asset in ['app.js', 'style.css']:
            assert client.get('/static/'+asset).status_code == 200
        assert client.get('/static/../app.py').status_code == 404


def test_browser_cookie_login_write_and_logout(tmp_path):
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        assert client.post('/api/v1/session').status_code == 401
        response = client.post('/api/v1/session', headers=AUTH)
        assert response.status_code == 204
        cookie = response.headers['set-cookie']
        assert 'HttpOnly' in cookie and 'SameSite=strict' in cookie
        assert TOKEN not in cookie
        assert client.get('/api/v1/subjects').status_code == 200
        assert client.post('/api/v1/subjects', headers=ORIGIN, json={'title':'Browser subject'}).status_code == 201
        assert client.delete('/api/v1/session', headers=ORIGIN).status_code == 204
        assert client.get('/api/v1/subjects').status_code == 401


def test_cookie_csrf_protection_and_bearer_compatibility(tmp_path):
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        client.post('/api/v1/session', headers=AUTH)
        for headers in [{}, {'Origin':'https://other.example'}, {'Origin':'http://localhost:6666'}]:
            assert client.post('/api/v1/subjects', headers=headers, json={'title':'Blocked'}).status_code == 403
        assert client.get('/api/v1/subjects', headers={'Sec-Fetch-Site':'same-site'}).status_code == 403
        assert client.get('/api/v1/subjects', headers={'Authorization':'Bearer incorrect'}).status_code == 401
        assert client.post('/api/v1/subjects', headers=AUTH, json={'title':'CLI'}).status_code == 201
        assert len(client.get('/api/v1/subjects').json()) == 1
