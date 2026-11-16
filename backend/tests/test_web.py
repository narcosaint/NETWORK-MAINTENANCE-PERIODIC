from http_client import ASGIClient
from app.main import app


def test_login_page_and_assets_are_same_origin_with_security_headers():
    client = ASGIClient(app)
    response = client.get('/')
    assert response.status_code == 200
    assert '<html lang="id">' in response.text
    assert 'id="login-form"' in response.text
    assert response.headers['cache-control'] == 'no-store'
    assert "script-src 'self'" in response.headers['content-security-policy']
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    for path, content_type in [('/assets/dashboard-v2.js', 'javascript'), ('/assets/dashboard-v2.css', 'text/css'), ('/assets/app.js', 'javascript'), ('/assets/hotel-detail.js', 'javascript'), ('/assets/sampling.js', 'javascript'), ('/assets/sampling-service.js', 'javascript'), ('/assets/sampling.css', 'text/css'), ('/assets/speedtest.js', 'javascript'), ('/assets/librespeed/speedtest_worker.js', 'javascript'), ('/assets/style.css', 'text/css')]:
        asset = client.get(path)
        assert asset.status_code == 200
        assert content_type in asset.headers['content-type']
        assert asset.headers['x-content-type-options'] == 'nosniff'
    assert client.get('/assets/missing.js').status_code == 404
