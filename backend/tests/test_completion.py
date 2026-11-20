import base64
from copy import deepcopy
from io import BytesIO
from uuid import uuid4
import pytest
from pypdf import PdfReader
from test_modules import client, isolated_lifespan
from test_hotel_visits import setup_hotel, mutate, image_bytes
from test_speedtests import METRICS, transfers


def completed_area_visit(client,monkeypatch,tmp_path,actual_transfer=True,areas=2,photos=True):
    api,_=client
    monkeypatch.setenv('PHOTO_STORAGE_ROOT',str(tmp_path/'photos'))
    for flag in ('SAMPLING_MASTER_ENABLED','SAMPLING_OBSERVATIONS_ENABLED','SAMPLING_FIELD_ENABLED','SAMPLING_SPEEDTEST_ENABLED'):
        monkeypatch.setenv(flag,'true')
    monkeypatch.setenv('PUBLIC_SPEEDTEST_ORIGIN','https://testserver')
    admin,tech,other,visit,_,_=setup_hotel(api);path='/hotel-visits/'+visit['id']
    visit=mutate(api,path,tech,'/check-in',{'device_time':'2026-11-19T00:00:00Z','gps_exception_reason':'Indoor QA'}).json()
    response=api.post(path+'/sampling-locations',headers=tech,json={'id':str(uuid4()),'expected_visit_version':visit['version'],
        'floor_name':'Lantai QA','reason':'Actual scope','points':[{'name':'Area 101'},{'name':'Koridor'}][:areas]})
    assert response.status_code==201,response.text
    report={'form_version':2,'backbone_mode':'both','fo':{'download_mbps':55,'upload_mbps':40},
        'wireless':{'download_mbps':30,'upload_mbps':20,'signal_dbm':-60,'link_test_download_mbps':70,'link_test_upload_mbps':60},
        'summary':'QA valid report <unsafe>','work_status':'completed','router_connector':'normal','switch_connector':'normal',
        'signal_test':'good','blank_spot':False,'hotspot':True,
        **{k+'_notes':'Inspected' for k in ('router_connector','switch_connector','signal_test','blank_spot','hotspot')}}
    saved=mutate(api,path,tech,'/report',{'report':report},method='put');assert saved.status_code==200,saved.text
    visit=saved.json()
    points=visit['sampling_coverage']['floors'][0]['points']
    for original in points:
        visit=api.get(path,headers=tech).json();point=next(p for p in visit['sampling_coverage']['floors'][0]['points'] if p['id']==original['id'])
        route=path+'/sampling-sessions/'+point['id']
        connection={'source':'android_native','observed_at':'2026-11-19T00:00:00Z','transport':'wifi','ssid':'QA network','bssid':'aa:bb:cc:dd:ee:ff','frequency_mhz':5180,'rssi_dbm':-65}
        response=api.post(route+'/observations',headers=tech,json={'id':str(uuid4()),'expected_visit_version':visit['version'],
            'expected_session_version':point['version'],'captured_at':'2026-11-19T00:00:00Z','notes':{'condition':'good','action':'Checked'},'wifi_connection':connection})
        assert response.status_code==201,response.text
        visit=response.json()['visit'];point=next(p for p in visit['sampling_coverage']['floors'][0]['points'] if p['id']==point['id'])
        if actual_transfer:
            binding={'id':str(uuid4()),'network_handle':'12345','source':'android_native'}
            response=api.post('https://testserver'+route+'/speedtests',headers=tech,json={'id':str(uuid4()),'expected_visit_version':visit['version'],
                'expected_session_version':point['version'],'connection':connection,'binding':binding})
            assert response.status_code==201,response.text
            started=response.json();transfers(api,started['transfer'])
            response=api.post(route+'/speedtests/'+started['attempt']['id']+'/finish',headers=tech,json={'result':{'status':'completed','metrics':METRICS},'connection':connection,'binding':binding})
            assert response.status_code==200,response.text
        else:
            response=api.post(route+'/speedtests/failures',headers=tech,json={'id':str(uuid4()),'expected_visit_version':visit['version'],
                'expected_session_version':point['version'],'reason':'Internet unavailable at location'})
            assert response.status_code==201,response.text
        for category in (('ap','area') if photos else ()):
            upload_photo(api,path,tech,point['id'],category)
    return api,admin,tech,other,path


def upload_photo(api,path,tech,point_id=None,category='router'):
    visit=api.get(path,headers=tech).json()
    payload={'id':str(uuid4()),'expected_version':visit['version'],'session_id':point_id,'category':category,
        'caption':'QA photo','captured_at':'2026-11-19T00:00:00Z','content_type':'image/png','image_base64':base64.b64encode(image_bytes()).decode()}
    response=api.post(path+'/evidence',headers=tech,json=payload)
    assert response.status_code==201,response.text
    return payload,response.json()


def signature(api,path,tech):
    visit=api.get(path,headers=tech).json();review=api.get(path+'/completion',headers=tech).json()
    assert review['ready'],review['errors']
    payload={'id':str(uuid4()),'expected_version':visit['version'],'document_digest':review['document_digest'],
        'name':'PIC Hotel QA','position':'Duty Manager','consent':True,'strokes':[[[i/20,0.4+(i%3)/20] for i in range(12)]]}
    response=api.post(path+'/pic-signature',headers=tech,json=payload)
    assert response.status_code==201,response.text
    return payload,response.json()


def test_complete_transfer_photo_pic_submit_pdf_and_approval(client,monkeypatch,tmp_path):
    api,admin,tech,other,path=completed_area_visit(client,monkeypatch,tmp_path)
    assert api.get(path+'/completion',headers=other).status_code==404
    assert api.get(path+'/report.pdf',headers=tech).status_code==409
    assert mutate(api,path,tech,'/check-out',{'device_time':'2026-11-19T01:00:00Z','gps_exception_reason':'Indoor QA'}).status_code==409
    payload,signed=signature(api,path,tech)
    assert signed['completion']['can_submit'] and all(p['speedtest_accepted'] for p in signed['completion']['points'])
    assert api.post(path+'/pic-signature',headers=tech,json=payload).json()['replayed']
    assert api.post(path+'/pic-signature',headers=admin,json=payload).status_code==403
    assert api.post(path+'/pic-signature',headers=other,json=payload).status_code==404
    assert api.post(path+'/pic-signature',headers=tech,json={**payload,'name':'Altered'}).status_code==409
    photo=api.get(path,headers=tech).json()['evidence'][0]
    assert api.get(path+'/evidence/'+photo['id'],headers=other).status_code==404
    assert api.get(path+'/evidence/'+photo['id']).status_code==401
    assert api.get(path+'/evidence/'+photo['id']+'/thumbnail',headers=tech).status_code==200
    pdf=api.get(path+'/report.pdf',headers=tech)
    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')
    text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    for value in ('Backbone Fiber Optic','Wireless Backbone','Local Area Network','Area 101','Koridor','PIC Hotel QA','Duty Manager','QA valid report <unsafe>','70','55','Download (Mbps)','RSSI (dBm)'):
        assert value in text,value
    assert api.get(path+'/report-download',headers=other).status_code==404
    encoded=api.get(path+'/report-download',headers=tech).json();assert base64.b64decode(encoded['data_base64']).startswith(b'%PDF')
    submitted=mutate(api,path,tech,'/check-out',{'device_time':'2026-11-19T01:00:00Z','gps_exception_reason':'Indoor QA'})
    assert submitted.status_code==200,submitted.text
    approved=mutate(api,path,admin,'/review',{'decision':'approved','reason':'Verified complete report'})
    assert approved.status_code==200,approved.text
    assert api.get(path+'/completion',headers=tech).json()['signature']['name']=='PIC Hotel QA'
    assert api.post(path+'/evidence',headers=tech,json={**payload}).status_code==422
    pdf=api.get(path+'/report.pdf',headers=admin)
    assert 'Disetujui supervisor' in PdfReader(BytesIO(pdf.content)).pages[0].extract_text()
    # Master edits must not rewrite or invalidate a signed monthly report.
    from app import models as m
    from sqlalchemy.orm import Session
    with Session(client[1]) as session:
        visit=session.get(m.HotelVisit,__import__('uuid').UUID(path.split('/')[-1]))
        session.get(m.Hotel,visit.hotel_id).name='Renamed after maintenance'
        session.get(m.User,visit.technician_id).name='Renamed technician'
        session.commit()
    pdf=api.get(path+'/report.pdf',headers=admin)
    assert pdf.status_code==200
    text=''.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    assert 'Hotel-wide test' in text and 'Renamed after maintenance' not in text



def test_edits_invalidate_signature_failed_tests_need_action_and_revision_resigns(client,monkeypatch,tmp_path):
    api,admin,tech,_,path=completed_area_visit(client,monkeypatch,tmp_path,actual_transfer=False)
    _,signed=signature(api,path,tech)
    assert all(p['failed_with_reason'] for p in signed['completion']['points'])
    report=api.get(path,headers=tech).json()['report'];report['summary']='Changed after signature'
    assert mutate(api,path,tech,'/report',{'report':report},method='put').status_code==200
    assert api.get(path+'/completion',headers=tech).json()['signature'] is None
    assert api.get(path+'/report.pdf',headers=tech).status_code==409
    signature(api,path,tech)
    assert mutate(api,path,tech,'/check-out',{'device_time':'2026-11-19T01:00:00Z','gps_exception_reason':'Indoor QA'}).status_code==200
    assert mutate(api,path,admin,'/review',{'decision':'revision_requested','reason':'Review changes'}).status_code==200
    # Entering revision requires a fresh PIC review even before content edits.
    assert api.get(path+'/completion',headers=tech).json()['signature'] is None
    signature(api,path,tech)
    assert mutate(api,path,tech,'/resubmit').status_code==200


def test_photo_replay_scope_bytes_missing_and_blank_signature(client,monkeypatch,tmp_path):
    api,_,tech,_,path=completed_area_visit(client,monkeypatch,tmp_path)
    payload,created=upload_photo(api,path,tech)
    retry=api.post(path+'/evidence',headers=tech,json={**payload,'expected_version':created['visit']['version']})
    assert retry.status_code==201 and retry.json()['replayed']
    assert api.post(path+'/evidence',headers=tech,json={**payload,'caption':'different'}).status_code==409
    assert api.post(path+'/evidence',headers=tech,json={**payload,'id':str(uuid4()),'session_id':str(uuid4()),'category':'area'}).status_code==404
    blank={'id':str(uuid4()),'expected_version':created['visit']['version'],'document_digest':'a'*64,'name':'PIC','position':'Manager','consent':True,'strokes':[[[0,0]]*12]}
    assert api.post(path+'/pic-signature',headers=tech,json=blank).status_code==422
    signature(api,path,tech)
    next((tmp_path/'photos').glob('*.jpg')).unlink()
    assert api.get(path+'/completion',headers=tech).json()['ready'] is False
    assert api.get(path+'/report.pdf',headers=tech).status_code==409


def test_one_actual_area_without_photos_completes_and_exports(client,monkeypatch,tmp_path):
    api,_,tech,_,path=completed_area_visit(client,monkeypatch,tmp_path,areas=1,photos=False)
    visit=api.get(path,headers=tech).json()
    assert len(visit['sampling_coverage']['floors'][0]['points'])==1
    assert not visit['evidence']
    _,signed=signature(api,path,tech)
    assert signed['completion']['can_submit']
    pdf=api.get(path+'/report.pdf',headers=tech)
    assert pdf.status_code==200
    assert 'Area 101' in ''.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)


def test_pdf_brand_filename_wireless_order_and_scanner_omission(client,monkeypatch,tmp_path):
    api,_,tech,_,path=completed_area_visit(client,monkeypatch,tmp_path,areas=1,photos=False)
    visit=api.get(path,headers=tech).json();point=visit['sampling_coverage']['floors'][0]['points'][0]
    route=path+'/sampling-sessions/'+point['id']+'/observations'
    response=api.post(route,headers=tech,json={'id':str(uuid4()),'expected_visit_version':visit['version'],
        'expected_session_version':point['version'],'captured_at':'2026-11-19T00:00:00Z',
        'notes':{'condition':'good','notes':'Perangkat bagus; pembersihan'},
        'wifi_scan':{'source':'android_native','observed_at':'2026-11-19T00:00:00Z','cached':True,
        'networks':[{'ssid':'SCANNER_MUST_NOT_APPEAR','bssid':'aa:bb:cc:dd:ee:02','observed_at':'2026-11-19T00:00:00Z',
        'cached':True,'frequency_mhz':5180,'rssi_dbm':-60}]}})
    assert response.status_code==201,response.text
    signature(api,path,tech)
    response=api.get(path+'/report.pdf',headers=tech)
    pdf=PdfReader(BytesIO(response.content));text='\n'.join(page.extract_text() for page in pdf.pages)
    assert 'SCANNER_MUST_NOT_APPEAR' not in text
    assert 'QA network' in text
    assert 'Perangkat bagus; pembersihan' in text
    wireless=text[text.index('C. Wireless Backbone'):text.index('D. Local Area Network')]
    labels=['Signal Strength (dBm)','Link Test Radio Download (Mbps)','Link Test Radio Upload (Mbps)',
        'Bandwidth Test Download (Mbps)','Bandwidth Test Upload (Mbps)']
    assert [wireless.index(label) for label in labels]==sorted(wireless.index(label) for label in labels)
    assert len(list(pdf.pages[0].images))>=2
    assert 'Nusa Maintenance-Hotel-wide test-2026-11.pdf' in response.headers['content-disposition']
    assert api.get(path+'/report-download',headers=tech).json()['filename']=='Nusa Maintenance-Hotel-wide test-2026-11.pdf'
    from app.maintenance_completion import report_filename
    filename=report_filename({'hotel':{'name':'../Hotel \"Injected\" / Bali'},'planned_date':'2026-11-19'})
    assert '..' not in filename and '/' not in filename and '\"' not in filename
