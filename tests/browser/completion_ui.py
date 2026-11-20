"""Android UI -> real FastAPI -> disposable DB -> signed PDF. Never production."""
import sys, threading, tempfile, os
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'backend/tests')]
from playwright.sync_api import sync_playwright,expect
from sqlalchemy import create_engine,event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session
from pytest import MonkeyPatch
from app.main import app
from app.api import db,_login_attempts
from app.models import Base,User
from app.security import hash_password
from http_client import ASGIClient
from test_completion import completed_area_visit
from test_hotel_visits import image_bytes
from pypdf import PdfReader
from io import BytesIO
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def run():
 engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
 @event.listens_for(engine,'connect')
 def fk(c,r):c.execute('PRAGMA foreign_keys=ON')
 Base.metadata.create_all(engine)
 with Session(engine) as s:
  s.add(User(username='admin',name='QA admin',role='supervisor',active=True,password_hash=hash_password('strong-secret-123')));s.commit()
 def override():
  with Session(engine) as s:yield s
 old=dict(app.dependency_overrides);app.dependency_overrides[db]=override;_login_attempts.clear();mp=MonkeyPatch()
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'android-app/dist')))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with tempfile.TemporaryDirectory(prefix='hotel-completion-browser-') as tmp:
   api,admin,tech,other,path=completed_area_visit((ASGIClient(app),engine),mp,Path(tmp))
   with ThreadPoolExecutor(max_workers=1) as worker,sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page(viewport={'width':390,'height':900},accept_downloads=True)
    page.set_default_timeout(15000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));lost=[False];offline=[False]
    def bridge(route):
     if offline[0]:route.abort('internetdisconnected');return
     parsed=urlsplit(route.request.url);target=parsed.path.removeprefix('/api')+('?' + parsed.query if parsed.query else '')
     headers={k:v for k,v in route.request.headers.items() if k in ('authorization','content-type')}
     response=worker.submit(api.request,route.request.method,target,headers=headers,content=route.request.post_data_buffer).result()
     if lost[0] and target.endswith('/pic-signature'):
      lost[0]=False;route.abort('internetdisconnected');return
     route.fulfill(status=response.status_code,content_type=response.headers.get('content-type','application/json'),body=response.content)
    page.route('**/api/**',bridge);page.goto(f'http://127.0.0.1:{server.server_port}')
    page.get_by_label('Username',exact=True).fill('hotel_tech');page.get_by_label('Password',exact=True).fill('strong-secret-456');page.get_by_role('button',name='Masuk',exact=True).click()
    page.get_by_role('navigation',name='Navigasi utama').get_by_role('button',name='Profil',exact=True).click()
    expect(page.get_by_role('heading',name='Kontak & wilayah kerja',exact=True)).to_be_visible()
    page.get_by_label('Nomor WhatsApp',exact=True).fill('+62 812-3456-7890')
    page.get_by_label('Email kantor',exact=True).fill('engineer@example.test')
    page.get_by_label('Divisi',exact=True).fill('Network Operations')
    page.get_by_label('Wilayah kerja',exact=True).fill('Bali')
    page.context.set_offline(True)
    page.get_by_role('button',name='Simpan Profil',exact=True).click()
    expect(page.get_by_role('alert').filter(has_text='Offline. Draf profil')).to_be_visible()
    page.get_by_role('navigation',name='Navigasi utama').get_by_role('button',name='Beranda',exact=True).click()
    page.context.set_offline(False)
    page.get_by_role('navigation',name='Navigasi utama').get_by_role('button',name='Profil',exact=True).click()
    expect(page.get_by_label('Wilayah kerja',exact=True)).to_have_value('Bali')
    page.get_by_role('button',name='Simpan Profil',exact=True).click()
    expect(page.get_by_text('Profil tersimpan di server.',exact=True)).to_be_visible()
    profile=worker.submit(api.get,'/auth/me/profile',headers=tech).result().json()
    assert profile['phone']=='+6281234567890' and profile['division']=='Network Operations'
    assert worker.submit(api.get,'/auth/me/profile',headers=other).result().json()['phone'] is None
    page.get_by_label('Wilayah kerja',exact=True).fill('Denpasar')
    conflict=worker.submit(api.put,'/auth/me/profile',headers=tech,json={**{k:v for k,v in profile.items() if k!='version'},'expected_version':profile['version'],'division':'NOC'}).result()
    assert conflict.status_code==200,conflict.text
    page.get_by_role('button',name='Simpan Profil',exact=True).click()
    expect(page.get_by_text('Profil server sudah berubah. Bandingkan sebelum menyimpan draf.',exact=True)).to_be_visible()
    expect(page.get_by_label('Wilayah kerja',exact=True)).to_have_value('Denpasar')
    page.get_by_role('button',name='Gunakan draf setelah review',exact=True).click()
    page.get_by_role('button',name='Simpan Profil',exact=True).click()
    expect(page.get_by_text('Profil tersimpan di server.',exact=True)).to_be_visible()
    assert worker.submit(api.get,'/auth/me/profile',headers=tech).result().json()['work_area']=='Denpasar'
    page.get_by_role('navigation',name='Navigasi utama').get_by_role('button',name='Beranda',exact=True).click()
    page.get_by_role('button',name='Buka maintenance',exact=False).first.click()
    page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Review',exact=True).click()
    expect(page.get_by_text('Seluruh pemeriksaan wajib sudah lengkap.',exact=True)).to_be_visible()
    page.get_by_role('button',name='Unduh / bagikan PDF',exact=True).click()
    expect(page.get_by_role('alert').filter(has_text='PDF final tersedia setelah tanda tangan')).to_be_visible()
    page.get_by_role('button',name='Simpan tanda tangan PIC',exact=True).click()
    alert=page.get_by_role('alert').filter(has_text='Isi nama, jabatan, tanda tangan')
    expect(alert).to_be_visible()
    bounds=alert.bounding_box();main=page.locator('.app-content').bounding_box()
    assert main['y']<=bounds['y'] and bounds['y']+bounds['height']<=main['y']+main['height']
    page.get_by_role('button',name='Check-out & kirim laporan',exact=True).click()
    expect(page.get_by_role('alert').filter(has_text='Simpan tanda tangan PIC untuk laporan terbaru')).to_be_visible()

    page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Network Test',exact=True).click()
    page.locator('.floor-points .area-row>button:first-child').first.click()
    page.locator('#sampling-panel').wait_for()
    expect(page.get_by_role('button',name='Catat gagal uji',exact=False)).to_have_count(0)
    assert page.locator('section[aria-label="Wi-Fi Scanner"]').is_visible()
    assert not page.get_by_text('Riwayat pengujian area',exact=True).evaluate('(el)=>el.closest("details").open')
    assert not page.get_by_text('Temuan dan Tindakan',exact=True).first.evaluate('(el)=>el.closest("details").open')
    page.get_by_text('Temuan dan Tindakan',exact=True).first.click()
    page.get_by_label('Kondisi area',exact=True).select_option('good')
    page.get_by_label('Temuan dan Tindakan',exact=True).fill('Isian antrean lama')
    page.context.set_offline(True)
    page.get_by_role('button',name='Simpan Hasil',exact=True).click()
    expect(page.get_by_role('alert').filter(has_text='antrean perangkat')).to_be_visible()
    page.context.set_offline(False)
    latest=worker.submit(api.get,path,headers=tech).result().json()
    first=latest['sampling_coverage']['floors'][0]['points'][0]
    from uuid import uuid4
    independent=worker.submit(api.post,path+'/sampling-sessions/'+first['id']+'/observations',headers=tech,json={
     'id':str(uuid4()),'expected_visit_version':latest['version'],'expected_session_version':first['version'],
     'captured_at':'2026-11-19T00:10:00Z','notes':{**first['observation']['notes'],'recommendation':'Server recommendation stays'}}).result()
    assert independent.status_code==201,independent.text
    page.get_by_label('Temuan dan Tindakan',exact=True).fill('Perangkat bagus; pembersihan selesai')
    assert page.get_by_label('Temuan dan Tindakan',exact=True).evaluate('(el)=>getComputedStyle(el).resize')=='none'
    page.get_by_label('Kategori foto',exact=True).select_option(label='Foto area sampling')
    page.get_by_label('Keterangan',exact=True).fill('Foto area dari HP')
    page.get_by_label('Pilih foto dari perangkat',exact=True).set_input_files([
     {'name':'area.png','mimeType':'image/png','buffer':image_bytes()},
     {'name':'area-2.png','mimeType':'image/png','buffer':image_bytes()}])
    expect(page.locator('.photo-grid article')).to_have_count(2)
    page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Review',exact=True).click()
    expect(page.get_by_role('button',name='Simpan tanda tangan PIC',exact=True)).to_be_enabled()
    page.get_by_label('Keterangan',exact=True).fill('Dokumentasi router lewat Android')
    page.get_by_label('Ambil / pilih foto',exact=True).set_input_files([
     {'name':'router.png','mimeType':'image/png','buffer':image_bytes()},
     {'name':'router-2.png','mimeType':'image/png','buffer':image_bytes()}])
    expect(page.get_by_role('button',name='Simpan tanda tangan PIC',exact=True)).to_be_enabled()
    labels=page.get_by_label('Kategori',exact=True).locator('option').all_text_contents()
    assert all(label==label.upper() for label in labels),labels
    expect(page.get_by_label('Alasan GPS check-out tidak tersedia',exact=False)).to_have_count(0)
    expect(page.get_by_role('button',name='Muat ulang untuk review ulang',exact=False)).to_have_count(0)
    # The stale queued request differs from a newer local draft and from the server.
    latest=worker.submit(api.get,path,headers=tech).result().json()
    first=latest['sampling_coverage']['floors'][0]['points'][0]
    clash=worker.submit(api.post,path+'/sampling-sessions/'+first['id']+'/observations',headers=tech,json={
     'id':str(uuid4()),'expected_visit_version':latest['version'],'expected_session_version':first['version'],
     'captured_at':'2026-11-19T00:11:00Z','notes':{**first['observation']['notes'],'notes':'Server technician edit'}}).result()
    assert clash.status_code==201,clash.text
    page.get_by_role('button',name='Review Hasil PDF',exact=True).click()
    expect(page.locator('#area-conflict')).to_be_visible()
    expect(page.locator('#area-conflict')).to_contain_text('Perangkat bagus; pembersihan selesai')
    expect(page.locator('#area-conflict')).to_contain_text('Server technician edit')
    page.get_by_role('button',name='Gunakan isian perangkat setelah review',exact=True).click()
    expect(page.locator('#area-conflict')).to_have_count(0)
    # Preview is a genuine PDF generated from the shared database.
    with page.expect_download() as download:
     page.get_by_role('button',name='Review Hasil PDF',exact=True).click()
    assert 'DRAF' in PdfReader(download.value.path()).pages[0].extract_text()
    assert download.value.suggested_filename.startswith('Nusa Maintenance-DRAF-Hotel-wide test-2026-11')
    current=worker.submit(api.get,path,headers=tech).result().json()
    assert len(current['evidence'])==8,current['evidence']
    assert current['sampling_coverage']['floors'][0]['points'][0]['observation']['notes']['notes']=='Perangkat bagus; pembersihan selesai'
    assert current['sampling_coverage']['floors'][0]['points'][0]['observation']['wifi_connection']['ssid']=='QA network'
    assert current['sampling_coverage']['floors'][0]['points'][0]['observation']['notes']['recommendation']=='Server recommendation stays'
    page.get_by_label('Nama PIC',exact=True).fill('PIC dari Android');page.get_by_label('Jabatan PIC',exact=True).fill('Engineering Manager')
    canvas=page.get_by_label('Area tanda tangan PIC',exact=True);canvas.scroll_into_view_if_needed();r=canvas.bounding_box()
    page.mouse.move(r['x']+25,r['y']+r['height']/2);page.mouse.down()
    for i in range(20):page.mouse.move(r['x']+25+i*8,r['y']+r['height']/2+(i%3)*5)
    page.mouse.up();page.get_by_role('checkbox',name='Saya sebagai PIC',exact=False).check()
    lost[0]=True;page.get_by_role('button',name='Simpan tanda tangan PIC',exact=True).click()
    expect(page.get_by_role('alert').filter(has_text='Server tidak dapat dihubungi')).to_be_visible()
    page.get_by_role('button',name='Simpan tanda tangan PIC',exact=True).click()
    expect(page.get_by_text('Tanda tangan PIC tersimpan.',exact=True)).to_be_visible()
    history=worker.submit(api.get,path+'/history',headers=tech).result().json()
    assert len([e for e in history if e['action']=='pic_signed'])==1
    with page.expect_download() as download:
     page.get_by_role('button',name='Unduh / bagikan PDF',exact=True).click()
    assert download.value.suggested_filename=='Nusa Maintenance-Hotel-wide test-2026-11.pdf'
    artifacts=ROOT/'artifacts/completion';artifacts.mkdir(parents=True,exist_ok=True);download.value.save_as(artifacts/'qa-signed-report.pdf')
    text='\n'.join(p.extract_text() for p in PdfReader(download.value.path()).pages)
    for expected in ('PIC dari Android','Engineering Manager','Backbone Fiber Optic','Wireless Backbone','Local Area Network','Area 101','Dokumentasi router lewat Android','Foto area dari HP'):
     assert expected in text,expected
    assert 'Wi-Fi scan' not in text
    # Offline re-open uses a visibly labelled cached PDF, no silent submit.
    page.context.set_offline(True)
    expect(page.get_by_role('button',name='Check-out & kirim laporan',exact=True)).to_be_disabled()
    with page.expect_download():page.get_by_role('button',name='Unduh / bagikan PDF',exact=True).click()
    expect(page.get_by_text('Membuka salinan PDF terakhir yang diunduh',exact=False)).to_be_visible()
    page.context.set_offline(False)
    expect(page.get_by_role('button',name='Check-out & kirim laporan',exact=True)).to_be_enabled()
    page.evaluate("() => { navigator.geolocation.getCurrentPosition = (_, fail) => fail({code:1,message:'GPS unavailable'}); }")
    page.get_by_role('button',name='Check-out & kirim laporan',exact=True).click()
    expect(page.get_by_text('Laporan dikirim. Menunggu review supervisor.',exact=True)).to_be_visible()
    current=worker.submit(api.get,path,headers=tech).result().json();assert current['status']=='submitted'
    for width in (360,390,768):
     page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
    dest=ROOT/'artifacts/completion';dest.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(dest/'submitted-pic-pdf.png'),full_page=True)
    assert not errors,errors;browser.close()
  print('PASS: actual API browser flow: own-account profile/offline/conflict, photo upload, reviewed draft PDF, canvas PIC, lost-ack signature retry, final PDF, submit, responsive. Fixture radio/metrics; no physical-device claim.')
 finally:
  server.shutdown();server.server_close();mp.undo();app.dependency_overrides.clear();app.dependency_overrides.update(old);engine.dispose()
if __name__=='__main__':run()
