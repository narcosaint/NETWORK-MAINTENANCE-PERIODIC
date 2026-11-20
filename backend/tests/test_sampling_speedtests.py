from copy import deepcopy
from uuid import uuid4, UUID
import pytest
from test_modules import client, isolated_lifespan
from test_sampling_observations import ready
from test_speedtests import transfers, METRICS
from app import speedtest_api as engine


@pytest.fixture(autouse=True)
def clear_live():
    engine._live.clear()
    yield
    engine._live.clear()


def prepared(api, monkeypatch):
    admin, tech, other, path, point, payload, _ = ready(api, monkeypatch)
    monkeypatch.setenv('SAMPLING_SPEEDTEST_ENABLED', 'true')
    payload.pop('notes');payload.pop('captured_at')
    payload['connection']={'source':'android_native','transport':'wifi','observed_at':'2026-11-18T00:00:00Z',
        'ssid':'QA only','bssid':'aa:bb:cc:dd:ee:ff','frequency_mhz':5180,'rssi_dbm':-65}
    route=path+'/sampling-sessions/'+point['id']+'/speedtests'
    return admin,tech,other,path,point,payload,route


def test_point_runs_do_not_share_results_or_apply_to_legacy_ap(client,monkeypatch):
    api,_=client
    admin,tech,other,path,point,payload,route=prepared(api,monkeypatch)
    assert api.post(route,headers=admin,json=payload).status_code==403
    assert api.post(route,headers=other,json=payload).status_code==404
    response=api.post(route,headers=tech,json=payload)
    assert response.status_code==201,response.text
    started=response.json();attempt=started['attempt'];run=started['transfer']
    assert api.post(route,headers=tech,json=payload).json()['attempt']['id']==attempt['id']
    assert 'transfer' not in api.post(route,headers=tech,json=payload).json()
    assert len(api.get(route,headers=tech).json())==1
    assert api.post('/network-speedtests/'+run['id']+'/finish',headers=tech,
        json={'status':'completed','metrics':METRICS}).status_code==409
    transfers(api,run)
    done=api.post(route+'/'+attempt['id']+'/finish',headers=tech,json={
        'result':{'status':'completed','metrics':{k:v for k,v in METRICS.items() if k!='jitter_ms'}},
        'connection':payload['connection']})
    assert done.status_code==200,done.text
    saved=done.json()['attempt']
    assert saved['status']=='completed' and saved['run']['metrics']['jitter_ms'] is None
    assert saved['run']['can_apply'] is False and saved['completion_accepted'] is False
    assert saved['run']['context']['radio_verified'] is False
    visit=done.json()['visit'];points=visit['sampling_coverage']['floors'][0]['points']
    assert len(points[0]['speedtests'])==1 and not points[1]['speedtests']
    assert not any(item['result'] or item['speedtests'] for item in visit['devices'] if item['device']['device_type']=='ap')
    # Same AP at the second location needs a separate actual run.
    second=deepcopy(payload);second.update(id=str(uuid4()),expected_visit_version=visit['version'],expected_session_version=points[1]['version'])
    second_route=path+'/sampling-sessions/'+points[1]['id']+'/speedtests'
    response=api.post(second_route,headers=tech,json=second)
    assert response.status_code==201,response.text
    assert response.json()['transfer']['id']!=run['id']
    assert api.post(route+'/'+response.json()['attempt']['id']+'/finish',headers=tech,
        json={'result':{'status':'failed','error':'QA failure'}}).status_code==404
    assert api.get(route,headers=other).status_code==404


def test_connection_change_or_missing_transfers_cannot_complete(client,monkeypatch):
    api,_=client
    _,tech,_,path,_,payload,route=prepared(api,monkeypatch)
    started=api.post(route,headers=tech,json=payload).json()
    transfers(api,started['transfer'])
    changed={**payload['connection'],'bssid':'aa:bb:cc:dd:ee:01'}
    response=api.post(route+'/'+started['attempt']['id']+'/finish',headers=tech,json={
        'result':{'status':'completed','metrics':METRICS},'connection':changed})
    assert response.status_code==200,response.text
    assert response.json()['attempt']['status']=='failed'
    assert response.json()['attempt']['run']['metrics'] is None
    assert response.json()['attempt']['finding']
    assert api.post(route+'/'+started['attempt']['id']+'/finish',headers=tech,json={
        'result':{'status':'failed','error':'Retry'}}).status_code==409
    current=response.json()['visit'];point=current['sampling_coverage']['floors'][0]['points'][0]
    second={**payload,'id':str(uuid4()),'expected_visit_version':current['version'],'expected_session_version':point['version']}
    started=api.post(route,headers=tech,json=second).json()
    result=api.post(route+'/'+started['attempt']['id']+'/finish',headers=tech,json={
        'result':{'status':'completed','metrics':METRICS},'connection':payload['connection']})
    assert result.json()['attempt']['status']=='failed' and result.json()['attempt']['run']['metrics'] is None


def test_failure_is_reasoned_idempotent_and_scoped(client,monkeypatch):
    api,_=client
    _,tech,_,path,point,payload,route=prepared(api,monkeypatch)
    failure={k:v for k,v in payload.items() if k!='connection'}
    failure['reason']='Wi-Fi tidak dapat dipakai di lokasi ini'
    response=api.post(route+'/failures',headers=tech,json=failure)
    assert response.status_code==201,response.text
    assert response.json()['attempt']['finding']==failure['reason']
    assert response.json()['attempt']['run'] is None
    assert api.post(route+'/failures',headers=tech,json=failure).json()['replayed'] is True
    assert api.post(route+'/failures',headers=tech,json={**failure,'reason':'Different'}).status_code==409
    assert api.post(route+'/failures',headers=tech,json={**failure,'id':str(uuid4()),'reason':'  '}).status_code==422
    assert api.post(route,headers=tech,json=payload).status_code==409
    monkeypatch.delenv('SAMPLING_SPEEDTEST_ENABLED')
    assert api.get(route,headers=tech).status_code==503


@pytest.mark.parametrize('matching_binding', [True, False])
def test_native_ticket_cors_is_scoped_and_finish_requires_same_binding(client, monkeypatch, matching_binding):
    api, _ = client
    _, tech, _, _, _, payload, route = prepared(api, monkeypatch)
    monkeypatch.setenv('PUBLIC_SPEEDTEST_ORIGIN', 'https://measure.test')
    binding = {'id': str(uuid4()), 'network_handle': '123456', 'source': 'android_native'}
    payload['binding'] = binding
    response = api.post('https://measure.test' + route, headers=tech, json=payload)
    assert response.status_code == 201, response.text
    started = response.json()
    run = started['transfer']
    assert run['context']['transport'] == 'direct_https'
    base = run['transfer_base']
    cors = {'Origin': 'https://localhost', 'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'X-Speedtest-Token'}
    response = api.options(base + '/ping', headers=cors)
    assert response.status_code == 204
    assert response.headers['access-control-allow-origin'] == 'https://localhost'
    assert 'access-control-allow-credentials' not in response.headers
    assert api.options(base + '/ping', headers={**cors, 'Access-Control-Request-Headers': 'Authorization'}).status_code == 403
    assert 'access-control-allow-origin' not in api.options(base + '/ping', headers={**cors, 'Origin': 'https://evil.test'}).headers
    assert 'access-control-allow-origin' not in api.options('/auth/login', headers=cors).headers
    assert api.options(base.replace(run['id'], str(uuid4())) + '/ping', headers=cors).status_code == 403
    assert api.get(base + '/ping', headers={'Origin': 'https://localhost'}).status_code == 401
    response = api.get(base + '/ping', headers={'Origin': 'https://localhost', 'X-Speedtest-Token': run['transfer_token']})
    assert response.status_code == 200 and response.headers['access-control-allow-origin'] == 'https://localhost'
    transfers(api, run)
    finished = api.post(route + '/' + started['attempt']['id'] + '/finish', headers=tech, json={
        'result': {'status': 'completed', 'metrics': METRICS}, 'connection': payload['connection'],
        'binding': binding if matching_binding else {**binding, 'id': str(uuid4())}})
    assert finished.status_code == 200, finished.text
    attempt = finished.json()['attempt']
    assert attempt['status'] == ('completed' if matching_binding else 'failed')
    assert bool(attempt['run']['metrics']) == matching_binding
    assert attempt['completion_accepted'] is False
    assert api.options(base + '/ping', headers=cors).status_code == 403



def test_phone_network_test_needs_no_inventory_or_mac_match(client,monkeypatch):
    from test_hotel_visits import setup_hotel, mutate
    from sqlalchemy import select,func
    from sqlalchemy.orm import Session
    from app import models as m
    api,engine=client
    admin,tech,other,visit,items,_=setup_hotel(api)
    for item in items[2:]:
        assert api.delete('/devices/'+item['id'],headers=admin).status_code==204
    for flag in ('SAMPLING_MASTER_ENABLED','SAMPLING_FIELD_ENABLED','SAMPLING_SPEEDTEST_ENABLED'):
        monkeypatch.setenv(flag,'true')
    path='/hotel-visits/'+visit['id']
    checked=mutate(api,path,tech,'/check-in',{'device_time':'2026-11-19T00:00:00Z','gps_exception_reason':'QA indoor'}).json()
    data={'id':str(uuid4()),'expected_visit_version':checked['version'],'floor_name':'Actual floor','reason':'Field location','points':[{'name':'Connected phone area'}]}
    created=api.post(path+'/sampling-locations',headers=tech,json=data).json()['visit']
    point=created['sampling_coverage']['floors'][0]['points'][0]
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(m.Device).where(m.Device.device_type=='ap'))==0
        devices=session.scalar(select(func.count()).select_from(m.Device))
        visit_devices=session.scalar(select(func.count()).select_from(m.HotelVisitDevice))
    # Actual phone BSSID deliberately has no inventory entry; no dummy AP is created.
    connection={'source':'android_native','transport':'wifi','observed_at':'2026-11-19T00:00:00Z','ssid':'Phone connected network','bssid':'AA:BB:CC:DD:EE:01','frequency_mhz':5180,'rssi_dbm':-61}
    payload={'id':str(uuid4()),'expected_visit_version':created['version'],'expected_session_version':point['version'],'connection':connection}
    route=path+'/sampling-sessions/'+point['id']+'/speedtests'
    result=api.post(route,headers=tech,json=payload)
    assert result.status_code==201,result.text
    started=result.json();run=started['transfer']
    assert run.get('visit_device_id') is None
    assert run['context']['measurement_scope']=='phone_connection' and run['context']['network']=='connected_wifi'
    assert 'access_point' not in run['context']
    assert run['context']['connection_start']['rssi_dbm']==-61
    assert api.get('/network-speedtests/'+run['id'],headers=other).status_code==404
    assert api.get('/network-speedtests/'+run['id'],headers=tech).status_code==200
    transfers(api,run)
    finished=api.post(route+'/'+started['attempt']['id']+'/finish',headers=tech,json={'result':{'status':'completed','metrics':METRICS},'connection':connection})
    assert finished.status_code==200 and finished.json()['attempt']['status']=='completed'
    assert finished.json()['attempt']['run']['can_apply'] is False
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(m.Device))==devices
        assert session.scalar(select(func.count()).select_from(m.HotelVisitDevice))==visit_devices
        saved=session.get(m.NetworkSpeedtest,UUID(run['id']))
        assert saved.visit_device_id is None and saved.sampling_session_id==UUID(point['id'])


def test_assigned_ap_metadata_does_not_override_current_phone_network(client,monkeypatch):
    api,_=client
    _,tech,_,_,_,payload,route=prepared(api,monkeypatch)
    payload['connection']['bssid']='00:11:22:33:44:55'
    started=api.post(route,headers=tech,json=payload)
    assert started.status_code==201,started.text
    assert started.json()['transfer']['context']['connection_start']['bssid']=='00:11:22:33:44:55'
