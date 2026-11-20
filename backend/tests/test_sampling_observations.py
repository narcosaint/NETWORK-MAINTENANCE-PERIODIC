from copy import deepcopy
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app import models as m
from test_modules import client, isolated_lifespan
from test_hotel_visits import mutate, checkout
from test_sampling_coverage import configured


def ready(api, monkeypatch):
    admin, tech, other, visit, _, _, config, _ = configured(api, monkeypatch)
    monkeypatch.setenv('SAMPLING_OBSERVATIONS_ENABLED', 'true')
    path = '/hotel-visits/' + visit['id']
    coverage = api.post(path + '/sampling-coverage', headers=admin, json=config).json()
    point = coverage['floors'][0]['points'][0]
    assert mutate(api, path, tech, '/check-in', {'device_time': '2026-11-16T00:00:00Z',
        'gps_exception_reason': 'Isolated test'}).status_code == 200
    current = api.get(path, headers=tech).json()
    payload = {'id': str(uuid4()), 'expected_visit_version': current['version'],
        'expected_session_version': point['version'], 'captured_at': '2026-11-16T00:01:00Z',
        'notes': {'condition': 'problem', 'findings': 'Sinyal putus', 'notes': 'Catatan aktual teknisi',
                  'action': 'Periksa kabel', 'recommendation': 'Ganti konektor'}}
    route = path + '/sampling-sessions/' + point['id'] + '/observations'
    return admin, tech, other, path, point, payload, route


def test_observation_scope_replay_and_unchanged_completion(client, monkeypatch):
    api, engine = client
    admin, tech, other, path, point, payload, route = ready(api, monkeypatch)
    before = api.get(path, headers=tech).json()
    assert api.post(route, headers=admin, json=payload).status_code == 403
    assert api.post(route, headers=other, json=payload).status_code == 404
    result = api.post(route, headers=tech, json=payload)
    assert result.status_code == 201, result.text
    saved = result.json()
    assert saved['visit']['version'] == before['version'] + 1
    assert saved['visit']['report'] == before['report']
    assert saved['observation']['session_version'] == point['version'] + 1
    assert saved['observation']['completion_accepted'] is False
    assert saved['observation']['radio_verified'] is False
    assert saved['observation']['wifi_connection'] is None
    assert saved['visit']['sampling_coverage']['floors'][0]['points'][0]['status'] == 'untested'
    again = api.post(route, headers=tech, json=payload).json()
    assert again['replayed'] is True and again['visit']['version'] == saved['visit']['version']
    assert again['observation']['id'] == payload['id']
    changed = deepcopy(payload); changed['notes']['findings'] = 'Different'
    assert api.post(route, headers=tech, json=changed).status_code == 409
    stale = deepcopy(payload); stale['id'] = str(uuid4()); stale['notes']['findings'] = 'Conflicting stale edit'
    assert api.post(route, headers=tech, json=stale).status_code == 409
    sibling = before['sampling_coverage']['floors'][0]['points'][1]
    wrong_route = path + '/sampling-sessions/' + sibling['id'] + '/observations'
    assert api.post(wrong_route, headers=tech, json=payload).status_code == 409
    assert api.get(wrong_route, headers=tech).json() == []
    assert len(api.get(route, headers=admin).json()) == 1
    assert api.get(route, headers=other).status_code == 404
    assert checkout(api, path, tech).status_code == 409
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(m.SamplingObservation)) == 1
    monkeypatch.delenv('SAMPLING_OBSERVATIONS_ENABLED')
    assert api.post(route, headers=tech, json=payload).status_code == 503
    # Saved evidence remains readable from visit detail, including after disabling writes.
    assert api.get(path, headers=tech).json()['sampling_coverage']['floors'][0]['points'][0]['observation']['id'] == payload['id']


def test_client_radio_observation_keeps_trust_and_point_scope(client, monkeypatch):
    api, _ = client
    _, tech, _, path, _, payload, route = ready(api, monkeypatch)
    payload['wifi_connection'] = {'source': 'android_native', 'observed_at': payload['captured_at'],
        'transport': 'wifi', 'ssid': 'Measured SSID', 'bssid': 'AA:BB:CC:DD:EE:FF',
        'frequency_mhz': 5180, 'rssi_dbm': -65, 'link_speed_mbps': 0, 'ip_address': '192.0.2.2'}
    payload['wifi_scan'] = {'source': 'android_native', 'observed_at': payload['captured_at'],
        'cached': True, 'requested_band': '5 GHz', 'reason': 'OS scan cache',
        'networks': [{'ssid': '', 'bssid': 'AA:BB:CC:DD:EE:FF', 'observed_at': payload['captured_at'],
                     'cached': True, 'frequency_mhz': 5180, 'rssi_dbm': -65}]}
    response = api.post(route, headers=tech, json=payload)
    assert response.status_code == 201, response.text
    observation = response.json()['observation']
    assert observation['measurement_trust'] == 'client_reported'
    assert observation['radio_verified'] is False and observation['completion_accepted'] is False
    assert observation['wifi_connection']['link_speed_mbps'] == 0
    assert observation['wifi_scan']['networks'][0]['cached'] is True
    assert observation['wifi_scan']['requested_band'] == '5 GHz'
    second = deepcopy(payload)
    second.update(id=str(uuid4()), expected_visit_version=response.json()['visit']['version'],
                  expected_session_version=observation['session_version'])
    second['notes']['condition'] = 'good'; second['notes']['findings'] = ''
    assert api.post(route, headers=tech, json=second).status_code == 201
    history = api.get(route, headers=tech).json()
    assert len(history) == 2 and history[0]['id'] == second['id']
    assert history[1]['notes']['findings'] == payload['notes']['findings']
    assert api.get(route + '?limit=101', headers=tech).status_code == 422


@pytest.mark.parametrize('change', ['naive_time', 'no_findings', 'manual_wifi', 'cellular', 'fake_verification', 'bad_rssi', 'bad_mac'])
def test_reject_invalid_observation(change):
    from app.sampling_observation_schemas import ObservationCreate
    from pydantic import ValidationError
    data = {'id': str(uuid4()), 'expected_visit_version': 1, 'expected_session_version': 1,
        'captured_at': '2026-11-16T00:00:00Z', 'notes': {'condition': 'good'},
        'wifi_connection': {'source': 'android_native', 'observed_at': '2026-11-16T00:00:00Z', 'transport': 'wifi'}}
    if change == 'naive_time': data['captured_at'] = '2026-11-16T00:00:00'
    if change == 'no_findings': data['notes']['condition'] = 'problem'
    if change == 'manual_wifi': data['wifi_connection']['source'] = 'manual'
    if change == 'cellular': data['wifi_connection']['transport'] = 'cellular'
    if change == 'fake_verification': data['radio_verified'] = True
    if change == 'bad_rssi': data['wifi_connection']['rssi_dbm'] = -200
    if change == 'bad_mac': data['wifi_connection']['bssid'] = 'invalid'
    with pytest.raises(ValidationError): ObservationCreate.model_validate(data)


def test_reject_mislabelled_scan_cache_or_band():
    from app.sampling_observation_schemas import WifiScan
    from pydantic import ValidationError
    payload = {'source':'android_native','observed_at':'2026-11-16T00:00:00Z','cached':False,
        'requested_band':'5 GHz','networks':[{'ssid':'','bssid':'aa:bb:cc:dd:ee:ff',
            'frequency_mhz':5180,'rssi_dbm':-65,'cached':True}]}
    with pytest.raises(ValidationError): WifiScan.model_validate(payload)
    payload['cached'] = True
    payload['requested_band'] = '2.4 GHz'
    with pytest.raises(ValidationError): WifiScan.model_validate(payload)


def test_notes_only_preserve_radio_independent_edits_and_replay(client, monkeypatch):
    api, _ = client
    _, tech, _, path, point, payload, route = ready(api, monkeypatch)
    payload['wifi_connection'] = {'source':'android_native','observed_at':payload['captured_at'],
        'transport':'wifi','ssid':'Measured network','frequency_mhz':5180,'rssi_dbm':-60}
    payload['wifi_scan'] = {'source':'android_native','observed_at':payload['captured_at'],
        'cached':True,'networks':[]}
    first=api.post(route,headers=tech,json=payload)
    assert first.status_code==201,first.text
    sibling=first.json()['visit']['sampling_coverage']['floors'][0]['points'][1]
    sibling_route=path+'/sampling-sessions/'+sibling['id']+'/observations'
    sibling_payload={**payload,'id':str(uuid4()),'expected_session_version':sibling['version']}
    # A save on a different area may use the previous global version safely.
    second=api.post(sibling_route,headers=tech,json=sibling_payload)
    assert second.status_code==201,second.text
    notes_only={'id':str(uuid4()),'expected_visit_version':first.json()['visit']['version'],
        'expected_session_version':first.json()['observation']['session_version'],
        'captured_at':payload['captured_at'],'notes':{'condition':'attention','notes':'Temuan dan tindakan actual'}}
    saved=api.post(route,headers=tech,json=notes_only)
    assert saved.status_code==201,saved.text
    observation=saved.json()['observation']
    assert observation['wifi_connection']==first.json()['observation']['wifi_connection']
    assert observation['wifi_scan']==first.json()['observation']['wifi_scan']
    assert observation['visit_version']==second.json()['visit']['version']+1
    assert '_request' not in observation
    replay=api.post(route,headers=tech,json=notes_only)
    assert replay.status_code==201 and replay.json()['replayed']
    assert api.post(route,headers=tech,json={**notes_only,'wifi_connection':None}).status_code==409
    assert api.post(route,headers=tech,json={**notes_only,'id':str(uuid4()),'notes':{'condition':'attention','notes':'Conflicting new text'}}).status_code==409
    clear={**notes_only,'id':str(uuid4()),'expected_session_version':observation['session_version'],
        'wifi_connection':None,'wifi_scan':None}
    cleared=api.post(route,headers=tech,json=clear)
    assert cleared.status_code==201,cleared.text
    assert cleared.json()['observation']['wifi_connection'] is None


def test_stale_outbox_merges_independent_notes_and_preserves_new_radio(client,monkeypatch):
    api,_=client
    _,tech,_,path,point,payload,route=ready(api,monkeypatch)
    base={'condition':'good','notes':'','findings':'','action':'','recommendation':''}
    payload['notes']=base
    payload['wifi_connection']={'source':'android_native','observed_at':'2026-11-16T00:01:00Z','transport':'wifi','ssid':'Old snapshot','frequency_mhz':5180,'rssi_dbm':-60}
    first=api.post(route,headers=tech,json=payload).json()
    queued={**payload,'id':str(uuid4()),'expected_session_version':first['observation']['session_version'],
        'expected_visit_version':first['visit']['version'],'notes':{**base,'notes':'Pembersihan selesai'}}
    independent={**queued,'id':str(uuid4()),'notes':{**base,'recommendation':'Periksa uplink'},
        'wifi_connection':{**payload['wifi_connection'],'ssid':'Newest measured snapshot','observed_at':'2026-11-16T00:02:00Z'}}
    saved=api.post(route,headers=tech,json=independent)
    assert saved.status_code==201,saved.text
    merged=api.post(route,headers=tech,json=queued)
    assert merged.status_code==201,merged.text
    obs=merged.json()['observation']
    assert obs['notes']['notes']=='Pembersihan selesai'
    assert obs['notes']['recommendation']=='Periksa uplink'
    assert obs['wifi_connection']['ssid']=='Newest measured snapshot'
    assert obs['session_version']==saved.json()['observation']['session_version']+1
    assert api.post(route,headers=tech,json=queued).json()['replayed']
    collision={**queued,'id':str(uuid4()),'notes':{**base,'notes':'Different device edit'}}
    rejected=api.post(route,headers=tech,json=collision)
    assert rejected.status_code==409,rejected.text
    detail=rejected.json()['detail']
    assert detail['code']=='sampling_notes_conflict' and detail['fields']==['notes']
    assert detail['current_notes']['notes']=='Pembersihan selesai'
    assert detail['requested_notes']['notes']=='Different device edit'
    current=api.get(path,headers=tech).json()
    assert current['version']==merged.json()['visit']['version']
