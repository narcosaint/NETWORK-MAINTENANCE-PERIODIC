from copy import deepcopy
from uuid import uuid4, UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app import models as m
from test_modules import client, isolated_lifespan
from test_sampling_coverage import configured
from test_hotel_visits import mutate


def field_ready(api, monkeypatch, activate=False):
    admin, tech, other, visit, floor, points, payload, base = configured(api, monkeypatch)
    monkeypatch.setenv('SAMPLING_FIELD_ENABLED', 'true')
    path='/hotel-visits/'+visit['id']
    if activate:
        assert api.post(path+'/sampling-coverage', headers=admin, json=payload).status_code==201
    assert mutate(api,path,tech,'/check-in',{'device_time':'2026-11-18T00:00:00Z','gps_exception_reason':'QA indoor'}).status_code==200
    current=api.get(path,headers=tech).json()
    data={'id':str(uuid4()),'expected_visit_version':current['version'],'floor_name':'Area rooftop QA',
          'reason':'Lokasi aktual tambahan saat kunjungan QA', 'points':[{'name':'Dek lift QA','location':'Sisi barat','device_id':None}]}
    return admin,tech,other,path,current,data


def test_technician_can_start_field_scope_after_checkin_with_default_target_and_audit(client, monkeypatch):
    api,engine=client
    admin,tech,other,path,before,data=field_ready(api,monkeypatch)
    route=path+'/sampling-locations'
    assert api.post(route,headers=admin,json=data).status_code==403
    assert api.post(route,headers=other,json=data).status_code==404
    assert api.get(path+'/sampling-inventory',headers=other).status_code==404
    assert api.get(path+'/sampling-inventory',headers=tech).status_code==200
    response=api.post(route,headers=tech,json=data)
    assert response.status_code==201,response.text
    after=response.json()['visit'];floor=after['sampling_coverage']['floors'][0]
    assert after['version']==before['version']+1
    assert after['report']==before['report'] and after['devices']==before['devices']
    assert floor['target_count']==2 and len(floor['points'])==1
    assert floor['points'][0]['name']=='Dek lift QA' and floor['points'][0]['device'] is None
    assert floor['points'][0]['status']=='untested' and not floor['points'][0]['speedtests']
    assert after['sampling_coverage']['completion_available'] is True
    retry=api.post(route,headers=tech,json=data)
    assert retry.status_code==201 and retry.json()['replayed'] is True
    assert retry.json()['visit']['version']==after['version']
    assert api.post(route,headers=tech,json={**data,'reason':'Different'}).status_code==409
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(m.SamplingSession))==1
        event=session.get(m.HotelVisitEvent, UUID(data['id']))
        assert event.actor_id==UUID(before['technician_id']) and event.snapshot['field_request']=={**data,'coverage_floor_id':None}
    # A terminal visit cannot receive new scope, but replay stays read-only.
    with Session(engine) as session:
        visit=session.get(m.HotelVisit,UUID(before['id']));visit.status='submitted';session.commit()
    assert api.post(route,headers=tech,json={**data,'id':str(uuid4()),'expected_visit_version':after['version']}).status_code==409
    assert api.post(route,headers=tech,json=data).json()['replayed'] is True


def test_field_append_preserves_existing_coverage_and_rejects_stale_cross_scope_and_wrong_ap(client,monkeypatch):
    api,_=client
    admin,tech,other,path,before,data=field_ready(api,monkeypatch,activate=True)
    original=deepcopy(before['sampling_coverage']['floors'])
    route=path+'/sampling-locations'
    bad={**data,'expected_visit_version':1}
    assert api.post(route,headers=tech,json=bad).status_code==409
    bad={**data,'points':[{'name':'Missing AP','device_id':str(uuid4())}]}
    assert api.post(route,headers=tech,json=bad).status_code==422
    assert api.get(path,headers=tech).json()==before
    response=api.post(route,headers=tech,json=data)
    assert response.status_code==201,response.text
    after=response.json()['visit']
    assert after['sampling_coverage']['floors'][:1]==original
    newfloor=after['sampling_coverage']['floors'][1]
    extra={**data,'id':str(uuid4()),'expected_visit_version':after['version'], 'coverage_floor_id':newfloor['id'], 'points':[{'name':'Koridor timur QA'}]}
    del extra['floor_name']
    response=api.post(route,headers=tech,json=extra)
    assert response.status_code==201,response.text
    points=response.json()['visit']['sampling_coverage']['floors'][1]['points']
    assert len(points)==2 and points[0]==newfloor['points'][0]
    invalid={**extra,'id':str(uuid4()),'coverage_floor_id':str(uuid4()),'expected_visit_version':response.json()['visit']['version']}
    assert api.post(route,headers=tech,json=invalid).status_code==404
    monkeypatch.setenv('SAMPLING_FIELD_ENABLED','false')
    assert api.post(route,headers=tech,json=extra).status_code==503
    assert api.get(path,headers=tech).json()['sampling_coverage']['floors'][1]['points']==points


def test_field_request_validation(client,monkeypatch):
    api,_=client
    _,tech,_,path,_,data=field_ready(api,monkeypatch)
    route=path+'/sampling-locations'
    for patch in ({'reason':' '},{'points':[]},{'points':[{'name':'A'},{'name':' a '}]},{'coverage_floor_id':str(uuid4())}):
        assert api.post(route,headers=tech,json={**data,**patch}).status_code==422


def test_field_mapping_on_next_visit_does_not_rewrite_prior_snapshot_or_master(client,monkeypatch):
    api,engine=client
    admin,tech,_,path,before,data=field_ready(api,monkeypatch)
    first=api.post(path+'/sampling-locations',headers=tech,json=data).json()['visit']
    original=deepcopy(first['sampling_coverage']['floors'])
    other=api.post('/hotel-visits',headers=admin,json={
        'hotel_id':before['hotel_id'],'technician_id':before['technician_id'],
        'planned_date':before['planned_date']}).json()
    second_path='/hotel-visits/'+other['id']
    assert mutate(api,second_path,tech,'/check-in',{'device_time':'2026-11-18T00:00:00Z','gps_exception_reason':'QA second visit'}).status_code==200
    current=api.get(second_path,headers=tech).json()
    changed={**data,'id':str(uuid4()),'expected_visit_version':current['version'],
        'points':[{**data['points'][0],'location':'Lokasi aktual berubah pada kunjungan berikut'}]}
    response=api.post(second_path+'/sampling-locations',headers=tech,json=changed)
    assert response.status_code==201,response.text
    new=response.json()['visit']['sampling_coverage']['floors'][0]['points'][0]
    old=original[0]['points'][0]
    assert new['sampling_point_id']==old['sampling_point_id'] and new['id']!=old['id']
    assert new['location']!=old['location']
    assert api.get(path,headers=tech).json()['sampling_coverage']['floors']==original
    with Session(engine) as session:
        assert session.get(m.SamplingPoint,UUID(new['sampling_point_id'])).location==old['location']


def test_cancel_empty_area_preserves_rows_can_restore_and_rejects_evidence(client,monkeypatch):
    api,engine=client
    _,tech,other,path,_,data=field_ready(api,monkeypatch)
    created=api.post(path+'/sampling-locations',headers=tech,json=data).json()['visit']
    point=created['sampling_coverage']['floors'][0]['points'][0]
    route=path+'/sampling-sessions/'+point['id']+'/remove'
    payload={'id':str(uuid4()),'expected_visit_version':created['version'],'expected_session_version':point['version']}
    assert api.post(route,headers=other,json=payload).status_code==404
    removed=api.post(route,headers=tech,json=payload)
    assert removed.status_code==200,removed.text
    assert removed.json()['visit']['sampling_coverage']['floors']==[]
    assert api.post(route,headers=tech,json=payload).json()['replayed']
    with Session(engine) as session:assert session.get(m.SamplingSession,UUID(point['id'])) is not None
    restored=api.post(path+'/sampling-locations',headers=tech,json={**data,'id':str(uuid4()),'expected_visit_version':removed.json()['visit']['version']})
    assert restored.status_code==201,restored.text
    visit=restored.json()['visit'];same=visit['sampling_coverage']['floors'][0]['points'][0]
    assert same['id']==point['id']
    monkeypatch.setenv('SAMPLING_OBSERVATIONS_ENABLED','true')
    obs=api.post(path+'/sampling-sessions/'+point['id']+'/observations',headers=tech,json={'id':str(uuid4()),'expected_visit_version':visit['version'],'expected_session_version':same['version'],'captured_at':'2026-11-19T00:00:00Z','notes':{'condition':'good'}})
    assert obs.status_code==201,obs.text
    assert api.post(route,headers=tech,json={**payload,'id':str(uuid4()),'expected_visit_version':obs.json()['visit']['version'],'expected_session_version':same['version']+1}).status_code==409


def test_new_hotel_can_be_scheduled_without_inventory(client):
    from test_modules import login
    api,_=client;admin=login(api)
    hotel=api.post('/hotels',headers=admin,json={'name':'QA customer site'}).json()
    tech=api.post('/users',headers=admin,json={'username':'no_inventory_tech','name':'QA tech','role':'technician','password':'strong-secret-456'}).json()
    response=api.post('/hotel-visits',headers=admin,json={'hotel_id':hotel['id'],'technician_id':tech['id'],'planned_date':'2026-11-19'})
    assert response.status_code==201,response.text
    assert response.json()['devices']==[]
