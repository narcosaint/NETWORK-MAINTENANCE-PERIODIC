"""Read-only HTTPS/API compatibility checks; never sends account credentials."""
import argparse
import json
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def normalize_origin(value):
    url = urlsplit(value)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.path not in ('', '/') or url.query or url.fragment):
        raise ValueError('Origin harus HTTPS tanpa path, credential, query atau fragment')
    return value.rstrip('/')


def fetch(origin, path):
    try:
        with build_opener(NoRedirect()).open(origin + path, timeout=15) as response:
            body = response.read(2 * 1024 * 1024 + 1)
            if len(body) > 2 * 1024 * 1024:
                raise ValueError('Respons melebihi batas pemeriksaan')
            return response.status, json.loads(body)
    except HTTPError as error:
        # Status only; never print response bodies or login details.
        return error.code, None


def check(origin, phase5=False, request=fetch):
    origin = normalize_origin(origin)
    checks = []
    for path in ('/health', '/health/db'):
        status, body = request(origin, path)
        checks.append((path, status == 200 and body == {'status': 'ok'}))
    status, _ = request(origin, '/auth/me')
    checks.append(('anonymous /auth/me rejected', status == 401))
    status, spec = request(origin, '/openapi.json')
    paths = spec.get('paths', {}) if status == 200 and isinstance(spec, dict) else {}
    required = [('/auth/login', 'post'), ('/auth/me', 'get'), ('/hotel-visits', 'get')]
    if phase5:
        required += [('/sampling-capabilities', 'get'),
            ('/hotel-visits/{identifier}/sampling-sessions/{session_id}/speedtests', 'post'),
            ('/hotel-visits/{identifier}/sampling-sessions/{session_id}/speedtests/{attempt_id}/finish', 'post')]
    for path, method in required:
        checks.append((method.upper() + ' ' + path, method in paths.get(path, {})))
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origin')
    parser.add_argument('--phase5', action='store_true', help='Also require session speedtest routes')
    args = parser.parse_args()
    try:
        results = check(args.origin, args.phase5)
    except Exception as error:
        print('FAIL: ' + type(error).__name__ + ' (periksa URL, DNS, TLS dan koneksi)', file=sys.stderr)
        return 1
    for label, passed in results:
        print(('PASS: ' if passed else 'FAIL: ') + label)
    print('Pemeriksaan read-only; login akun dan uji APK tetap perlu diverifikasi terpisah.')
    return 0 if all(passed for _, passed in results) else 1


if __name__ == '__main__':
    sys.exit(main())
