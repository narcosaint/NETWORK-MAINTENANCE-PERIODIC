"""Web/Android -> actual FastAPI -> isolated SQLite. No production or Docker."""
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'backend/tests')]
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from playwright.sync_api import sync_playwright, expect
from app.main import app
from app.api import db, _login_attempts
from app.models import Base, User
from app.security import hash_password
from http_client import ASGIClient
from test_hotel_visits import setup_hotel


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run():
    prior_field = os.environ.get('SAMPLING_FIELD_ENABLED')
    os.environ['SAMPLING_FIELD_ENABLED'] = 'true'
    prior_gate = os.environ.get('SAMPLING_MASTER_ENABLED')
    prior_observations = os.environ.get('SAMPLING_OBSERVATIONS_ENABLED')
    prior_speedtests = os.environ.get('SAMPLING_SPEEDTEST_ENABLED')
    os.environ['SAMPLING_MASTER_ENABLED'] = 'true'
    os.environ['SAMPLING_OBSERVATIONS_ENABLED'] = 'true'
    os.environ['SAMPLING_SPEEDTEST_ENABLED'] = 'true'
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, record):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(username='admin', name='QA supervisor', role='supervisor', active=True,
                         password_hash=hash_password('strong-secret-123')))
        session.commit()
    previous_overrides = dict(app.dependency_overrides)
    def override():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[db] = override
    _login_attempts.clear()
    api = ASGIClient(app)
    admin, tech, _, visit, devices, _ = setup_hotel(api)
    servers = []
    def serve(directory):
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(directory)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f'http://127.0.0.1:{server.server_port}'
    try:
        web_origin = serve(ROOT / 'backend/app/web')
        android_origin = serve(ROOT / 'android-app/dist')
        with ThreadPoolExecutor(max_workers=1) as worker, sync_playwright() as p:
            def api_call(method, path, **kwargs):
                return worker.submit(api.request, method, path, **kwargs).result()
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 390, 'height': 1000})
            page.set_default_timeout(10000)
            errors = []
            offline = [False]
            drop_ack = [False]
            page.on('pageerror', lambda error: errors.append(str(error)))
            def bridge(route):
                if offline[0]:
                    route.abort('internetdisconnected')
                    return
                path = urlsplit(route.request.url).path
                if path.startswith('/api/'):
                    path = path.removeprefix('/api')
                query = urlsplit(route.request.url).query
                headers = {key: value for key, value in route.request.headers.items()
                           if key in ('authorization', 'content-type')}
                response = worker.submit(api.request, route.request.method, path + ('?' + query if query else ''),
                    headers=headers, content=route.request.post_data_buffer).result()
                if drop_ack[0] and route.request.method == 'POST' and (path.endswith('/observations') or path.endswith('/sampling-locations')):
                    drop_ack[0] = False
                    route.abort('internetdisconnected')
                    return
                route.fulfill(status=response.status_code, content_type='application/json', body=response.content)
            for pattern in ('**/hotels/**', '**/hotel-visits/**', '**/sampling-capabilities'):
                page.route(pattern, bridge)
            # Static files retain the exact /assets paths used by FastAPI.
            page.route('**/assets/**', lambda route: route.fulfill(
                path=str(ROOT / 'backend/app/web' / urlsplit(route.request.url).path.removeprefix('/assets/'))))
            page.goto(web_origin)
            data = {kind: api_call('GET', path, headers=admin).json() for kind, path in {
                'hotels': '/hotels', 'devices': '/devices', 'users': '/users', 'hotelvisits': '/hotel-visits',
                'visits': '/visits', 'schedules': '/schedules', 'templates': '/checklist-templates'}.items()}
            page.evaluate('''({token,user,data})=>{
                state.token=token;state.user=user;state.data=data;state.page='hotels';
                document.querySelector('#workspace').hidden=false;
                document.querySelector('#login-view').hidden=true;render();
            }''', {'token': admin['Authorization'].removeprefix('Bearer '),
                  'user': api_call('GET', '/auth/me', headers=admin).json(), 'data': data})
            page.evaluate('(id)=>openHotelDetail(id,"floors")', visit['hotel_id'])
            expect(page.locator('#hotel-detail-panel')).to_contain_text('Master sampling server')
            page.locator('#master-floor-create [name=name]').fill('Lantai QA <script>')
            page.locator('#master-floor-create button').click()
            expect(page.locator('[data-master-floor]')).to_have_count(1)
            floor_id = page.locator('[data-master-floor]').get_attribute('data-master-floor')
            for i in range(4):
                form = page.locator('[data-master-point-create]')
                form.locator('..').locator('summary').click()
                form.locator('[name=name]').fill(f'Titik {i} <img src=x>')
                form.locator('[name=position]').fill(str(i))
                form.locator('[name=device_id]').select_option(devices[2]['id'])
                form.locator('button').click()
                expect(page.locator('[data-master-point]')).to_have_count(i + 1)
            assert page.locator('#hotel-detail-panel script,#hotel-detail-panel img').count() == 0
            for width in (360, 390, 768, 1440):
                page.set_viewport_size({'width': width, 'height': 1000})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
            page.evaluate('(id)=>openSampling(id)', visit['id'])
            form = page.locator('#activate-sampling-coverage')
            expect(form).to_be_visible()
            form.locator('[name=sampling][value=ap]').check()
            form.locator('[name=reviewed]').check()
            form.locator('button').click()
            expect(page.locator('#server-coverage')).to_have_count(0)
            expect(page.locator('#activate-sampling-coverage')).to_have_count(0)
            assert page.evaluate('samplingPoints(samplingView)[0].points.length') == 4
            assert page.evaluate('samplingPoints(samplingView)[0].points.every(p=>p.session&&!p.item)')
            assert page.evaluate('samplingPoints(samplingView)[0].points.filter(p=>v2Evidence(p).done).length') == 0
            api_call('PATCH', f"/hotels/{visit['hotel_id']}/floors/{floor_id}", headers=admin,
                      json={'expected_version': 1, 'name': 'Master renamed'})
            page.evaluate('(id)=>openSampling(id)', visit['id'])
            expect(page.locator('.v2-dashboard')).to_contain_text('Lantai QA <script>')
            expect(page.locator('.v2-dashboard')).not_to_contain_text('Master renamed')
            current = api_call('GET', '/hotel-visits/' + visit['id'], headers=tech).json()
            assert api_call('POST', '/hotel-visits/' + visit['id'] + '/check-in', headers=tech, json={
                'expected_version': current['version'], 'device_time': '2026-11-16T00:00:00Z',
                'gps_exception_reason': 'Browser QA indoor'}).status_code == 200
            page.evaluate('''({token,user})=>{state.token=token;state.user=user;}''', {
                'token': tech['Authorization'].removeprefix('Bearer '),
                'user': api_call('GET', '/auth/me', headers=tech).json()})
            page.evaluate('(id)=>openSampling(id)', visit['id'])
            page.locator('.v2-floor summary').first.click()
            page.locator('[data-sampling-floor]').first.click()
            page.locator('[data-sampling-point]').first.click()
            page.get_by_role('tab', name='Foto & Catatan', exact=True).click()
            page.locator('[data-sampling-note=notes]').fill('Catatan Web tersimpan')
            page.locator('[data-observation-save]').click()
            expect(page.get_by_role('status').filter(has_text='Catatan titik tersimpan di server')).to_be_visible()
            assert page.evaluate('samplingFindPoint(samplingView).session.observation.notes.notes') == 'Catatan Web tersimpan'
            # Android consumes the same persisted snapshot from the real visit API.
            page.unroute_all()
            page.route('**/api/**', bridge)
            page.goto(android_origin)
            page.get_by_label('Username').fill('hotel_tech')
            page.get_by_label('Password', exact=True).fill('strong-secret-456')
            page.get_by_role('button', name='Masuk', exact=False).click()
            page.get_by_role('button', name='Buka maintenance', exact=False).first.click()
            expect(page.get_by_role('heading',name='Cakupan sampling kunjungan')).to_have_count(0)
            expect(page.locator('.app-content')).not_to_contain_text('Master renamed')
            page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button', name='Network Test', exact=True).click()
            expect(page.locator('.app-content')).to_contain_text('Lantai QA <script>')
            expect(page.locator('.floor-points .area-row>button:first-child')).to_have_count(4)
            expect(page.locator('.floor-card')).to_contain_text('0/4 area selesai')
            assert page.locator('.floor-points script,.floor-points img').count() == 0
            page.locator('.floor-points .area-row>button:first-child').first.click()
            page.locator('#sampling-panel').wait_for()
            page.get_by_text('Temuan dan Tindakan',exact=True).first.click()
            expect(page.get_by_label('Temuan dan Tindakan', exact=True)).to_have_value('Catatan Web tersimpan')
            page.get_by_label('Temuan dan Tindakan', exact=True).fill('Catatan Android diterima meski respons hilang')
            drop_ack[0] = True
            page.get_by_role('button', name='Simpan Hasil', exact=True).click()
            expect(page.locator('.app-content')).to_contain_text('Server tidak dapat dihubungi')
            page.get_by_role('button', name='Simpan Hasil', exact=True).click()
            expect(page.locator('.app-content')).to_contain_text('Hasil area tersimpan di server')
            current = api_call('GET', '/hotel-visits/' + visit['id'], headers=tech).json()
            point = current['sampling_coverage']['floors'][0]['points'][0]
            history = api_call('GET', f"/hotel-visits/{visit['id']}/sampling-sessions/{point['id']}/observations", headers=tech).json()
            assert len(history) == 2, history
            assert history[0]['notes']['notes'] == 'Catatan Android diterima meski respons hilang'
            # Selector navigates to a different area; it must not move previous notes.
            second_area=current['sampling_coverage']['floors'][0]['points'][1]
            expect(page.get_by_role('button',name='Simpan Hasil',exact=True)).to_be_visible()
            page.get_by_label('Lokasi sampling',exact=True).select_option(second_area['id'])
            page.get_by_text('Temuan dan Tindakan',exact=True).first.click()
            expect(page.get_by_label('Temuan dan Tindakan',exact=True)).to_be_visible()
            page.get_by_label('Temuan dan Tindakan',exact=True).fill('QA temuan khusus area kedua')
            page.get_by_role('button',name='Simpan Hasil',exact=True).click()
            expect(page.locator('.app-content')).to_contain_text('Hasil area tersimpan di server')
            second_history=api_call('GET',f"/hotel-visits/{visit['id']}/sampling-sessions/{second_area['id']}/observations",headers=tech).json()
            assert len(second_history)==1 and second_history[0]['notes']['notes']=='QA temuan khusus area kedua'
            page.get_by_label('Lokasi sampling',exact=True).select_option(point['id'])
            page.get_by_text('Temuan dan Tindakan',exact=True).first.click()
            expect(page.get_by_label('Temuan dan Tindakan',exact=True)).to_have_value('Catatan Android diterima meski respons hilang')
            current=api_call('GET','/hotel-visits/'+visit['id'],headers=tech).json()
            point=current['sampling_coverage']['floors'][0]['points'][0]
            # Synthetic QA radio payload in this disposable DB tests rendering and
            # caching only; this is not a physical Android radio measurement.
            from uuid import uuid4
            radio = {'id':str(uuid4()),'expected_visit_version':current['version'],
                'expected_session_version':point['version'],'captured_at':'2026-11-16T00:02:00Z',
                'notes':history[0]['notes'],
                'wifi_connection':{'source':'android_native','transport':'wifi','observed_at':'2026-11-16T00:02:00Z',
                    'ssid':'QA WiFi fixture','bssid':'aa:bb:cc:dd:ee:ff','frequency_mhz':5180,
                    'rssi_dbm':-65,'link_speed_mbps':0,'ip_address':'192.0.2.2','gateway':'192.0.2.1'},
                'wifi_scan':{'source':'android_native','observed_at':'2026-11-16T00:02:00Z',
                    'requested_band':'5 GHz','reason':'QA OS cache fixture','cached':True,'networks':[
                        {'ssid':'QA WiFi fixture','bssid':'aa:bb:cc:dd:ee:ff','frequency_mhz':5180,
                         'rssi_dbm':-65,'observed_at':'2026-11-16T00:01:30Z','cached':True},
                        {'ssid':'','bssid':'aa:bb:cc:dd:ee:01','frequency_mhz':5200,
                         'rssi_dbm':-75,'observed_at':'2026-11-16T00:01:30Z','cached':True}]}}
            assert api_call('POST', f"/hotel-visits/{visit['id']}/sampling-sessions/{point['id']}/observations",headers=tech,json=radio).status_code==201
            page.get_by_role('button',name='Muat ulang kunjungan',exact=True).click()
            expect(page.locator('.network-grid')).to_contain_text('QA WiFi fixture')
            page.locator('#sampling-panel').wait_for()
            expect(page.get_by_role('heading',name='Wi-Fi Scanner',exact=True)).to_be_visible()
            page.get_by_role('button',name='5 GHz',exact=True).click()
            expect(page.locator('.wifi-networks li')).to_have_count(2)
            expect(page.locator('.wifi-networks')).to_contain_text('SSID tersembunyi')
            expect(page.locator('.wifi-graph')).to_have_count(1)
            page.locator('#sampling-panel').wait_for()
            expect(page.get_by_role('button',name='Mulai Speedtest · Belum tersedia',exact=True)).to_be_disabled()
            expect(page.get_by_role('button',name='Catat gagal uji',exact=False)).to_have_count(0)
            page.get_by_role('button', name='Network Test', exact=True).click()
            # Technician adds real named field scope through Android -> actual API.
            page.get_by_role('button',name='Tambah Area',exact=True).click()
            page.get_by_label('Nama lantai / kelompok',exact=True).fill('Rooftop QA lapangan')
            page.get_by_label('Nama area 1',exact=True).fill('Lift barat QA')
            drop_ack[0]=True
            page.get_by_role('button',name='Simpan area',exact=True).click()
            expect(page.get_by_role('button',name='Kirim ulang area',exact=True)).to_be_enabled()
            page.get_by_role('button',name='Kirim ulang area',exact=True).click()
            expect(page.get_by_role('status').filter(has_text='Area tersimpan.')).to_be_visible()
            expect(page.locator('.floor-points .area-row>button:first-child')).to_have_count(5)
            updated=api_call('GET','/hotel-visits/'+visit['id'],headers=tech).json()
            fieldfloor=updated['sampling_coverage']['floors'][-1]
            assert fieldfloor['name']=='Rooftop QA lapangan' and fieldfloor['target_count']==2
            assert len(fieldfloor['points'])==1 and fieldfloor['points'][0]['device'] is None
            assert updated['sampling_coverage']['floors'][0]['points'][0]['id']==point['id']
            page.get_by_label('Lantai / kelompok area',exact=True).select_option(fieldfloor['id'])
            page.get_by_label('Nama area 1',exact=True).fill('Koridor utara QA')
            page.get_by_role('button',name='Simpan area',exact=True).click()
            expect(page.locator('.floor-points .area-row>button:first-child')).to_have_count(6)
            for width in (360, 390, 768):
                page.set_viewport_size({'width': width, 'height': 1000})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
            offline[0] = True
            page.get_by_role('button', name='Muat ulang kunjungan', exact=True).click()
            expect(page.locator('.app-content')).to_contain_text('Data cache perangkat')
            expect(page.locator('.floor-points .area-row>button:first-child')).to_have_count(6)
            artifacts = ROOT / 'artifacts/sampling-foundation'
            artifacts.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(artifacts / 'android-coverage-offline.png'), full_page=True)
            assert not errors, errors
            browser.close()
        print('PASS: Web -> FastAPI -> SQLite -> Android; immutable scope, per-session notes, lost-ack replay without duplicates, offline snapshot and responsive layout.')
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        engine.dispose()
        if prior_field is None: os.environ.pop('SAMPLING_FIELD_ENABLED', None)
        else: os.environ['SAMPLING_FIELD_ENABLED'] = prior_field
        if prior_gate is None: os.environ.pop('SAMPLING_MASTER_ENABLED', None)
        else: os.environ['SAMPLING_MASTER_ENABLED'] = prior_gate
        if prior_observations is None: os.environ.pop('SAMPLING_OBSERVATIONS_ENABLED', None)
        else: os.environ['SAMPLING_OBSERVATIONS_ENABLED'] = prior_observations
        if prior_speedtests is None: os.environ.pop('SAMPLING_SPEEDTEST_ENABLED', None)
        else: os.environ['SAMPLING_SPEEDTEST_ENABLED'] = prior_speedtests


if __name__ == '__main__':
    run()
