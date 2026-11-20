import pytest
from test_modules import client, isolated_lifespan
from test_hotel_visits import private_photos, setup_hotel, populate, mutate, checkout
from app.report_rules import conformity


@pytest.mark.parametrize('values,expected', [
    ((80,16,100,20,80),('conforming','calculated')),
    ((80,15.99,100,20,80),('not_conforming','calculated')),
    ((79.99,16,100,20,80),('not_conforming','calculated')),
    ((37.68,8,47.1,10,80),('conforming','calculated')),
    ((None,16,100,20,80),(None,'measurement_missing')),
    ((80,16,100,None,80),(None,'profile_missing')),
    ((80,16,100,20,None),(None,'profile_missing')),
])
def test_conformity_boundaries_missing_values_and_asymmetric_services(values,expected):
    assert conformity(*values)==expected


def test_site_identity_and_bandwidth_policy_are_authoritative_and_frozen(client):
    api,_=client
    admin,assigned,_,visit,devices,payload=setup_hotel(api)
    path='/hotel-visits/'+visit['id']
    populate(api,path,assigned,devices)
    site_id=payload['hotel_id']
    site=api.get('/hotels/'+site_id,headers=admin).json()
    data={k:v for k,v in site.items() if k not in ('id','created_at')}
    data.update(customer_name='PT Pelanggan Asli',maintenance_profile={
        'minimum_percent':80,'fo':{'download_mbps':100,'upload_mbps':20},
        'wireless':{'download_mbps':50,'upload_mbps':10}})
    assert api.put('/hotels/'+site_id,headers=assigned,json=data).status_code==403
    assert api.put('/hotels/'+site_id,headers=admin,json=data).status_code==200
    report=api.get(path,headers=assigned).json()['report']
    report['customer_company']='Spoofed customer'
    report['fo']={'download_mbps':80,'upload_mbps':15.9,'conformity':'conforming',
                  'agreement_download_mbps':1,'agreement_upload_mbps':1,'minimum_percent':1}
    saved=mutate(api,path,assigned,'/report',{'report':report},method='put')
    assert saved.status_code==200
    stored=saved.json()['report']
    assert stored['customer_company']=='PT Pelanggan Asli'
    assert stored['fo']['conformity']=='not_conforming'
    assert stored['fo']['agreement_upload_mbps']==20 and stored['fo']['minimum_percent']==80
    stored['fo']['upload_mbps']=16
    response=mutate(api,path,assigned,'/report',{'report':stored},method='put')
    assert response.json()['report']['fo']['conformity']=='conforming'
    assert checkout(api,path,assigned).status_code==200
    before=api.get(path+'/history',headers=admin).json()
    data['customer_name']='PT Nama Baru'
    data['maintenance_profile']['minimum_percent']=100
    assert api.put('/hotels/'+site_id,headers=admin,json=data).status_code==200
    assert api.get(path,headers=assigned).json()['report']['customer_company']=='PT Pelanggan Asli'
    assert api.get(path,headers=assigned).json()['report']['fo']['minimum_percent']==80
    assert api.get(path+'/history',headers=admin).json()==before
    assert mutate(api,path,admin,'/review',{'decision':'approved','reason':'Stored report policy reviewed'}).status_code==200


def test_new_report_requires_individual_lan_notes_and_cannot_downgrade(client):
    api,_=client
    _,assigned,_,visit,devices,_=setup_hotel(api)
    path='/hotel-visits/'+visit['id']
    populate(api,path,assigned,devices)
    report=api.get(path,headers=assigned).json()['report']
    assert report['form_version']==2
    for key in ['router_connector_notes','switch_connector_notes','signal_test_notes','blank_spot_notes','hotspot_notes']:
        bad={**report,key:'   '}
        assert mutate(api,path,assigned,'/report',{'report':bad},method='put').status_code==200
        response=checkout(api,path,assigned)
        assert response.status_code==409 and 'keterangan' in response.json()['detail']
    assert mutate(api,path,assigned,'/report',{'report':{**report,'form_version':1}},method='put').status_code==409
    assert mutate(api,path,assigned,'/report',{'report':report},method='put').status_code==200
    assert checkout(api,path,assigned).status_code==200


def test_legacy_report_remains_readable_without_reinterpreting_old_measurements(client):
    from uuid import UUID
    from sqlalchemy.orm import Session
    from app.models import HotelVisit
    api,engine=client
    admin,assigned,_,visit,devices,_=setup_hotel(api)
    path='/hotel-visits/'+visit['id']
    populate(api,path,assigned,devices)
    report=api.get(path,headers=assigned).json()['report']
    report['form_version']=1
    report['customer_company']='Historical customer'
    report['fo']={'agreement_mbps':50,'speedtest_mbps':45,'conformity':'conforming','source':'manual'}
    for key in ['router_connector_notes','switch_connector_notes','signal_test_notes','blank_spot_notes','hotspot_notes']:
        report.pop(key,None)
    with Session(engine) as session:
        stored=session.get(HotelVisit,UUID(visit['id']))
        stored.report=report
        session.commit()
    assert api.get(path,headers=assigned).json()['report']==report
    assert checkout(api,path,assigned).status_code==200
    assert mutate(api,path,admin,'/review',{'decision':'approved','reason':'Historical format reviewed'}).status_code==200
    assert api.get(path,headers=assigned).json()['report']==report



def test_numeric_wireless_link_test_roundtrips_without_dropping_legacy_values(client):
    from copy import deepcopy
    from test_speedtests import setup_sample
    from test_hotel_visits import mutate
    api,_=client
    _,tech,_,path,_=setup_sample(api)
    before=api.get(path,headers=tech).json()
    report=deepcopy(before['report'])
    report.update(form_version=2,backbone_mode='both',customer_feedback='QA saved feedback',lan_notes='QA legacy LAN')
    report['wireless']={'link_test_download_mbps':0,'link_test_upload_mbps':125.5,'tx_mbps':30,'rx_mbps':20,'ccq_percent':95,'link_test_radio':'QA legacy radio text'}
    result=mutate(api,path,tech,'/report',{'report':report},method='put')
    assert result.status_code==200,result.text
    saved=result.json()['report']
    assert saved['wireless']['link_test_download_mbps']==0
    assert saved['wireless']['link_test_upload_mbps']==125.5
    assert saved['wireless']['link_test_radio']=='QA legacy radio text' and saved['wireless']['tx_mbps']==30
    assert saved['customer_feedback']=='QA saved feedback' and saved['lan_notes']=='QA legacy LAN'
    saved['wireless']['link_test_upload_mbps']=-1
    assert mutate(api,path,tech,'/report',{'report':saved},method='put').status_code==422
