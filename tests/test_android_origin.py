"""Prevent readiness checks from accepting redirects, login pages or old API builds."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

spec = spec_from_file_location('origin_check', Path(__file__).resolve().parents[1] / 'scripts/check_android_origin.py')
module = module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize('origin', ['http://example.com', 'https://example.com/api', 'https://user:pass@example.com', 'https://example.com?token=x', 'https://example.com#x'])
def test_invalid_origins(origin):
    with pytest.raises(ValueError): module.normalize_origin(origin)


def fixture_request(origin, path):
    assert origin == 'https://qa.example.com'
    if path in ('/health', '/health/db'): return 200, {'status': 'ok'}
    if path == '/auth/me': return 401, None
    return 200, {'paths': {'/auth/login': {'post': {}}, '/auth/me': {'get': {}}, '/hotel-visits': {'get': {}}}}


def test_healthy_login_api_does_not_claim_phase5_ready():
    assert all(ok for _, ok in module.check('https://qa.example.com/', request=fixture_request))
    assert not all(ok for _, ok in module.check('https://qa.example.com', phase5=True, request=fixture_request))


def test_redirect_or_html_page_cannot_pass_health():
    for status, body in [(302, None), (200, '<html>login</html>')]:
        results = module.check('https://qa.example.com', request=lambda origin, path: (status, body))
        assert not all(ok for _, ok in results)

