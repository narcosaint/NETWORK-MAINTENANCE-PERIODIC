import pytest
from test_modules import client, isolated_lifespan
from test_hotel_visits import setup_hotel, mutate
from app import speedtest_api as speed


@pytest.fixture(autouse=True)
def isolated_speedtests(monkeypatch):
    speed._live.clear()
    monkeypatch.delenv('PUBLIC_SPEEDTEST_ORIGIN', raising=False)
    yield
    speed._live.clear()


def setup_sample(api):
    admin, assigned, other, visit, devices, _ = setup_hotel(api)
    path='/hotel-visits/'+visit['id']
    assert mutate(api,path,assigned,'/check-in',{'device_time':'2026-11-12T03:00:00Z','gps_exception_reason':'Test only'}).status_code==200
    assert mutate(api,path,assigned,'/samples',{'device_id':devices[2]['id'],'floor':'26','point':'2601'}).status_code==201
    detail=api.get(path,headers=assigned).json()
    item=next(i for i in detail['devices'] if i['device']['device_type']=='ap')
    return admin,assigned,other,path,item


def start(api,assigned,path,item,direct=False,network='hotel_wifi'):
    version=api.get(path,headers=assigned).json()['version']
    url=path+'/devices/'+item['id']+'/speedtests'
    if direct:url='https://measure.test'+url
    return api.post(url,headers={**assigned,**({'Origin':'https://measure.test'} if direct else {})},json={
        'expected_version':version,'band':'band_24','network':network,
        'wifi_confirmed':network=='hotel_wifi','observed_type':'unknown'})


def transfers(api,run):
    base=run['transfer_base'];headers={'X-Speedtest-Token':run['transfer_token']}
    for _ in range(3):assert api.get(base+'/ping',headers=headers).status_code==200
    response=api.get(base+'/download',headers=headers)
    assert response.status_code==200 and len(response.content)==speed.RESPONSE_BYTES
    assert response.headers['content-encoding']=='identity'
    assert 'no-store' in response.headers['cache-control']
    assert api.post(base+'/upload',headers=headers,content=b'x'*4096).status_code==200


# Synthetic client-reported measurements are fixtures, not real speed measurements.
METRICS={'download_mbps':40.5,'upload_mbps':20.2,'ping_ms':5.1,'jitter_ms':1.2}


def test_diagnostic_speedtest_is_saved_but_cannot_fill_ap(client):
    api,_=client
    admin,assigned,other,path,item=setup_sample(api)
    run=start(api,assigned,path,item).json()
    assert run['context']['transport']=='diagnostic_tunnel_or_local'
    assert api.get(run['transfer_base']+'/download').status_code==401
    assert api.get(run['transfer_base']+'/ping',headers={'X-Speedtest-Token':'wrong'}).status_code==401
    assert api.get('/network-speedtests/'+run['id'],headers=other).status_code==404
    transfers(api,run)
    finish=api.post('/network-speedtests/'+run['id']+'/finish',headers=assigned,json={'status':'completed','metrics':METRICS})
    assert finish.status_code==200 and finish.json()['metrics']==METRICS
    assert finish.json()['can_apply'] is False
    assert 'transfer_token' not in finish.json()
    version=api.get(path,headers=assigned).json()['version']
    apply=api.post(path+'/devices/'+item['id']+'/speedtests/'+run['id']+'/apply',headers=assigned,json={'expected_version':version})
    assert apply.status_code==409
    detail=api.get(path,headers=assigned).json()
    sample=next(i for i in detail['devices'] if i['id']==item['id'])
    assert not sample['result']
    assert len(sample['speedtests'])==1 and 'transfer_token' not in str(sample['speedtests'])
    assert api.get(run['transfer_base']+'/ping',headers={'X-Speedtest-Token':run['transfer_token']}).status_code==401


def test_https_confirmed_wifi_result_applies_without_overwriting_rf(client,monkeypatch):
    api,_=client
    _,assigned,_,path,item=setup_sample(api)
    result={'outcome':'pass','notes':'Real RF observations entered separately',
            'band_24':{'status':'measured','signal_dbm':-65,'channel':6,'bandwidth_mbps':10},
            'band_5':{'status':'unavailable','reason':'Not supported'}}
    assert mutate(api,path,assigned,'/devices/'+item['id']+'/result',{'result':result},method='put').status_code==200
    monkeypatch.setenv('PUBLIC_SPEEDTEST_ORIGIN','https://measure.test')
    run=start(api,assigned,path,item,direct=True).json()
    assert run['context']['transport']=='direct_https'
    transfers(api,run)
    saved=api.post('/network-speedtests/'+run['id']+'/finish',headers=assigned,json={'status':'completed','metrics':METRICS}).json()
    assert saved['can_apply'] is True
    version=api.get(path,headers=assigned).json()['version']
    apply_url=path+'/devices/'+item['id']+'/speedtests/'+run['id']+'/apply'
    assert api.post(apply_url,headers=assigned,json={'expected_version':version-1}).status_code==409
    response=api.post(apply_url,headers=assigned,json={'expected_version':version})
    assert response.status_code==200
    sample=next(i for i in response.json()['devices'] if i['id']==item['id'])
    assert sample['result']['band_24']['bandwidth_mbps']==40.5
    assert sample['result']['band_24']['signal_dbm']==-65
    assert sample['result']['band_24']['channel']==6
    assert sample['result']['automatic_speedtests']['band_24']['id']==run['id']
    assert sample['result']['automatic_speedtests']['band_24']['context']['radio_verified'] is False
    # Saving RF observations preserves provenance if the measured bandwidth stays.
    result['band_24']['bandwidth_mbps']=40.5
    response=mutate(api,path,assigned,'/devices/'+item['id']+'/result',{'result':result},method='put')
    assert 'automatic_speedtests' in next(i for i in response.json()['devices'] if i['id']==item['id'])['result']
    # Deliberate manual replacement loses the automatic provenance, not the run record.
    result['band_24']['bandwidth_mbps']=20
    response=mutate(api,path,assigned,'/devices/'+item['id']+'/result',{'result':result},method='put')
    sample=next(i for i in response.json()['devices'] if i['id']==item['id'])
    assert not sample['result'].get('automatic_speedtests')
    assert len(sample['speedtests'])==1
    assert api.post('/network-speedtests/'+run['id']+'/finish',headers=assigned,json={'status':'completed','metrics':METRICS}).status_code==409


def test_no_transfer_or_quota_error_never_produces_completed_numbers(client,monkeypatch):
    api,_=client
    _,assigned,_,path,item=setup_sample(api)
    run=start(api,assigned,path,item).json()
    saved=api.post('/network-speedtests/'+run['id']+'/finish',headers=assigned,json={'status':'completed','metrics':METRICS}).json()
    assert saved['status']=='failed' and saved['metrics'] is None
    run=start(api,assigned,path,item).json()
    monkeypatch.setattr(speed,'DOWNLOAD_LIMIT',1)
    response=api.get(run['transfer_base']+'/download',headers={'X-Speedtest-Token':run['transfer_token']})
    assert response.status_code==429
    saved=api.post('/network-speedtests/'+run['id']+'/finish',headers=assigned,json={'status':'completed','metrics':METRICS}).json()
    assert saved['status']=='failed' and saved['metrics'] is None and 'Batas' in saved['error']


def test_speedtest_permissions_cancellation_and_network_mismatch(client):
    api,_=client
    admin,assigned,other,path,item=setup_sample(api)
    version=api.get(path,headers=assigned).json()['version']
    url=path+'/devices/'+item['id']+'/speedtests'
    payload={'expected_version':version,'band':'band_24','network':'hotel_wifi','wifi_confirmed':True}
    assert api.post(url,headers=admin,json=payload).status_code==403
    assert api.post(url,headers=other,json=payload).status_code==404
    assert api.post(url,headers=assigned,json={**payload,'observed_type':'cellular'}).status_code==422
    assert api.post(url,headers=assigned,json={**payload,'wifi_confirmed':False}).status_code==422
    run=start(api,assigned,path,item).json()
    assert start(api,assigned,path,item).status_code==429
    assert api.post('/network-speedtests/'+run['id']+'/finish',headers=admin,json={'status':'aborted'}).status_code==403
    response=api.post('/network-speedtests/'+run['id']+'/finish',headers=assigned,json={'status':'aborted'})
    assert response.status_code==200 and response.json()['status']=='aborted' and response.json()['metrics'] is None
    assert api.post('/network-speedtests/'+run['id']+'/finish',headers=assigned,json={'status':'aborted'}).status_code==409
