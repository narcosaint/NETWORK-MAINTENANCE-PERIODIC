"""CORS only for an active purpose-bound Android transfer ticket, never API auth."""
import re
import time
from uuid import UUID
from fastapi import Response
from app import speedtest_api as engine
from app.sampling_speedtest_api import speedtests_enabled

PATTERN = re.compile(r'^/network-speedtests/transfer/([0-9a-fA-F-]{36})/(ping|download|upload)$')
ALLOWED_HEADERS = {'x-speedtest-token', 'content-type', 'content-encoding'}


async def native_transfer_cors(request, call_next):
    match = PATTERN.fullmatch(request.url.path)
    if not match or request.headers.get('origin') != 'https://localhost':
        return await call_next(request)
    allowed = False
    if speedtests_enabled():
        try:
            with engine._lock:
                live = engine._live.get(UUID(match[1]))
                allowed = bool(live and live.get('worker_origin') == 'https://localhost' and live['until'] > time.monotonic())
        except ValueError:
            pass
    if request.method == 'OPTIONS':
        headers = {value.strip().lower() for value in request.headers.get('access-control-request-headers','').split(',') if value.strip()}
        if not allowed or request.headers.get('access-control-request-method') not in ('GET','POST') or not headers <= ALLOWED_HEADERS:
            return Response(status_code=403, headers={'Cache-Control':'no-store'})
        response = Response(status_code=204)
    else:
        response = await call_next(request)
    if allowed:
        response.headers['Access-Control-Allow-Origin'] = 'https://localhost'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = ', '.join(sorted(ALLOWED_HEADERS))
        response.headers['Access-Control-Max-Age'] = '0'
        response.headers.append('Vary','Origin')
        response.headers['Cache-Control'] = 'no-store'
    return response
