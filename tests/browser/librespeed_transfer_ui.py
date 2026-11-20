"""Actual vendored worker -> cross-origin HTTPS -> FastAPI transfer endpoints.
Disposable SQLite, native radio/binding fixtures. Never a production measurement.
"""
import sys,threading,tempfile,subprocess,socket,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'backend/tests')]
from sqlalchemy import create_engine,event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from pytest import MonkeyPatch
from playwright.sync_api import sync_playwright
from app.main import app
from app.api import db,_login_attempts
from app.models import Base,User
from app.security import hash_password
from app import speedtest_api as speed
from http_client import ASGIClient
from test_sampling_speedtests import prepared
import uvicorn
from concurrent.futures import ThreadPoolExecutor

def run():
 engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
 @event.listens_for(engine,'connect')
 def fk(c,r):c.execute('PRAGMA foreign_keys=ON')
 Base.metadata.create_all(engine)
 with Session(engine) as s:s.add(User(username='admin',name='QA',role='supervisor',active=True,password_hash=hash_password('strong-secret-123')));s.commit()
 def override():
  with Session(engine) as s:yield s
 old=dict(app.dependency_overrides);app.dependency_overrides[db]=override;mp=MonkeyPatch();_login_attempts.clear();speed._live.clear()
 server=None
 try:
  mp.setattr(speed,'UPLOAD_LIMIT',16*1024*1024)
  api=ASGIClient(app);_,tech,_,path,point,payload,route=prepared(api,mp)
  from uuid import uuid4
  payload['binding']={'id':str(uuid4()),'network_handle':'12345','source':'android_native'}
  with tempfile.TemporaryDirectory(prefix='librespeed-https-qa-') as tmp:
   tmp=Path(tmp);key=tmp/'key.pem';cert=tmp/'cert.pem'
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
   sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen();port=sock.getsockname()[1];origin=f'https://localhost:{port}';mp.setenv('PUBLIC_SPEEDTEST_ORIGIN',origin)
   request_trace=[]
   async def traced(scope,receive,send):
    if scope['type']=='http':
     headers=dict(scope.get('headers',[]));request_trace.append((scope['method'],scope['path'],headers.get(b'origin',b'').decode(),headers.get(b'access-control-request-headers',b'').decode()))
    await app(scope,receive,send)
   server=uvicorn.Server(uvicorn.Config(traced,log_level='error',access_log=False,lifespan='off',ssl_keyfile=str(key),ssl_certfile=str(cert)))
   thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
   for _ in range(100):
    if server.started:break
    time.sleep(.05)
   assert server.started
   with ThreadPoolExecutor(max_workers=1) as api_worker,sync_playwright() as p:
    browser=p.chromium.launch(args=['--ignore-certificate-errors']);context=browser.new_context(ignore_https_errors=True,permissions=['local-network-access']);page=context.new_page()
    page.route('https://localhost/',lambda r:r.fulfill(content_type='text/html',body='<html><body>Isolated worker QA</body></html>'))
    page.route('https://localhost/speedtest_worker.js',lambda r:r.fulfill(content_type='application/javascript',path=str(ROOT/'backend/app/web/librespeed/speedtest_worker.js')))
    page.goto('https://localhost/');page.set_default_timeout(25000)
    started=api_worker.submit(api.post,origin+route,headers=tech,json=payload).result();assert started.status_code==201,started.text
    started=started.json();run=started['transfer'];base=origin+run['transfer_base']
    settings={'test_order':'P_D_U','url_dl':base+'/download','url_ul':base+'/upload','url_ping':base+'/ping','time_dl_max':2,'time_ul_max':8,'time_auto':False,'count_ping':5,'xhr_dlMultistream':2,'xhr_ulMultistream':1,'xhr_ul_blob_megabytes':4,'xhr_ignoreErrors':0,'telemetry_level':'disabled','getIp_ispInfo':False,'overheadCompensationFactor':1,'ping_allowPerformanceApi':False,'hotel_transfer_token':run['transfer_token'],'hotel_run_id':run['id'],'hotel_endpoint_origin':origin,'hotel_dl_budget_bytes':8*1024*1024,'hotel_ul_budget_bytes':speed.UPLOAD_LIMIT,'hotel_dl_chunk_bytes':speed.RESPONSE_BYTES}
    result=page.evaluate('''settings=>new Promise((resolve,reject)=>{const worker=new Worker('/speedtest_worker.js');const timeout=setTimeout(()=>{worker.terminate();reject(Error('worker timeout'));},22000);const poll=setInterval(()=>worker.postMessage('status'),100);worker.onerror=e=>reject(Error(e.message+" at "+e.filename+":"+e.lineno));worker.onmessage=e=>{const value=JSON.parse(e.data);if(value.testState>=4){clearTimeout(timeout);clearInterval(poll);worker.terminate();resolve(value);}};worker.postMessage('start '+JSON.stringify(settings));})''',settings)
    assert result['testState']==4 and all(str(result[k]).replace('.','',1).isdigit() and float(result[k])>0 for k in ('dlStatus','ulStatus','pingStatus')),result
    live=speed._live[__import__('uuid').UUID(run['id'])]
    assert live['upload']==speed.UPLOAD_LIMIT and live['download']==8*1024*1024 and live['error'] is None,live
    finish=api_worker.submit(api.post,route+'/'+started['attempt']['id']+'/finish',headers=tech,json={'result':{'status':'completed','metrics':{'download_mbps':float(result['dlStatus']),'upload_mbps':float(result['ulStatus']),'ping_ms':float(result['pingStatus']),'jitter_ms':float(result['jitterStatus'])}},'connection':payload['connection'],'binding':payload['binding']}).result()
    assert finish.status_code==200 and finish.json()['attempt']['status']=='completed',finish.text
    observation=finish.json()['visit']['sampling_coverage']['floors'][0]['points'][0]['observation']
    assert observation['wifi_connection']['bssid']==payload['connection']['bssid']
    assert not finish.json()['attempt']['run']['context']['radio_verified']
    print('PASS: actual LibreSpeed worker over cross-origin HTTPS/CORS uploads exactly the configured 16 MiB QA cap, stops within server budget, saves completed run and native connection snapshot. Radio/binding are QA fixtures.')
    browser.close()
 finally:
  if server:server.should_exit=True;thread.join(timeout=10)
  mp.undo();app.dependency_overrides.clear();app.dependency_overrides.update(old);speed._live.clear();engine.dispose()
if __name__=='__main__':run()
