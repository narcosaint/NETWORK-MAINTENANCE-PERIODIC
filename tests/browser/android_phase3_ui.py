"""Phase 3 React/Capacitor UI. Static build + intercepted API fixtures, no real DB."""
import copy
import os
import io
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from PIL import Image
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[2]
ARTIFACTS=ROOT/os.environ.get('ANDROID_UI_ARTIFACTS','artifacts/phase3')
PAYLOAD='<img src=x onerror="window.xss=true"><script>window.xss=true</script>'
USER={'id':'tech-qa','name':'Teknisi QA','username':'qa','role':'technician','active':True}
HOTEL={'id':'hotel-qa','name':'Hotel QA (fixture)','address':'Alamat QA','customer_name':'Pelanggan QA','maintenance_profile':{'minimum_percent':80,'fo':{'download_mbps':100,'upload_mbps':50}}}
VISIT={'id':'visit-qa','hotel_id':'hotel-qa','technician_id':USER['id'],'planned_date':'2026-11-13','status':'assigned','version':1,'report':{'form_version':2,'fo':{'speedtest_mbps':0,'agreement_mbps':20},'wireless':{'tx_mbps':30,'rx_mbps':40,'ccq_percent':90},'lan_notes':'Catatan format lama'},'site':HOTEL,'devices':[{'id':'ap-qa','device_id':'device-qa','device':{'id':'device-qa','name':'AP QA','device_type':'ap'},'floor':'2','point':'Koridor QA','result':{},'photos':[],'speedtests':[]}]}
class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def run():
    ARTIFACTS.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'android-app/dist')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            ctx=browser.new_context(viewport={'width':390,'height':844},permissions=['geolocation'],geolocation={'latitude':-7.25,'longitude':112.75,'accuracy':20})
            page=ctx.new_page();errors=[];writes=[];api_errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            visit=copy.deepcopy(VISIT);conflict=[False];expire=[False];empty=[False]
            def api(route):
                url=urlsplit(route.request.url);path=url.path.removeprefix('/api');method=route.request.method
                def respond(body,status=200):route.fulfill(status=status,content_type='application/json',body=json.dumps(body))
                if expire[0]:respond({'detail':'Expired'},401);return
                if path=='/auth/login':
                    data=route.request.post_data_json
                    if data['password']!='fixture-only':respond({'detail':'Invalid'},401)
                    else:respond({'access_token':'fixture-token','token_type':'bearer','expires_in':28800})
                    return
                if path=='/auth/me':respond(USER);return
                if path=='/auth/logout':route.fulfill(status=204);return
                if route.request.headers.get('authorization')!='Bearer fixture-token':api_errors.append(path)
                if method!='GET':writes.append((method,path,route.request.post_data_json))
                if path=='/hotels':respond([HOTEL]);return
                if path=='/hotel-visits':respond([] if empty[0] or parse_qs(url.query).get('offset')!=['0'] else [visit]);return
                if path=='/hotel-visits/visit-qa':respond(visit);return
                if path.endswith('/check-in'):
                    data=route.request.post_data_json
                    assert data['expected_version']==visit['version']
                    visit['version']+=1;visit['status']='in_progress';visit['checkin']={**data,'server_time':'2026-11-13T10:00:00Z'};respond(visit);return
                if path.endswith('/report'):
                    if conflict[0]:respond({'detail':'Conflict'},409);return
                    data=route.request.post_data_json
                    assert method=='PUT' and data['expected_version']==visit['version']
                    visit['report']=data['report'];visit['version']+=1;respond(visit);return
                api_errors.append(path);respond({'detail':'Unexpected fixture route'},404)
            page.route('**/api/**',api)
            origin=f'http://127.0.0.1:{server.server_port}'
            def assert_navigation_clearance():
                assert page.evaluate('''()=>{
                    const main=document.querySelector('.app-content').getBoundingClientRect();
                    const nav=document.querySelector('.bottom-nav').getBoundingClientRect();
                    return main.bottom<=nav.top+1&&main.top>=document.querySelector('.app-header').getBoundingClientRect().bottom-1&&nav.bottom<=innerHeight+1;
                }''')
            def screenshot_section(title,filename):
                page.get_by_role('heading',name=title,exact=True).evaluate('''el=>{const main=document.querySelector('.app-content');main.scrollTop+=el.closest('.card').getBoundingClientRect().top-main.getBoundingClientRect().top-12;}''')
                assert_navigation_clearance()
                page.screenshot(path=str(ARTIFACTS/filename),full_page=True)

            def login():
                page.get_by_label('Username',exact=True).fill('qa');page.get_by_label('Password',exact=True).fill('fixture-only')
                page.get_by_role('button',name='Masuk ke workspace').click()
                expect(page.get_by_role('heading',name='Dashboard Teknisi')).to_be_visible()
            def open_hotel():page.locator('.job-card').first.click();expect(page.get_by_role('heading',name='Informasi hotel')).to_be_visible()
            page.goto(origin)
            page.get_by_label('Username',exact=True).fill('qa');page.get_by_label('Password',exact=True).fill('wrong')
            page.get_by_role('button',name='Masuk ke workspace').click();expect(page.get_by_role('alert')).to_contain_text('Sesi berakhir atau username/password')
            login();expect(page.locator('.job-card')).to_have_count(1)
            for width in (360,390,430,768):
                page.set_viewport_size({'width':width,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),('dashboard',width)
            page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(ARTIFACTS/'dashboard-390.png'),full_page=True)
            page.get_by_role('navigation',name='Navigasi utama').get_by_role('button',name='Jadwal').click()
            open_hotel();page.get_by_role('button',name='Check-in dengan GPS',exact=True).click()
            expect(page.get_by_role('status').filter(has_text='Check-in tersimpan')).to_be_visible()
            checked=writes[-1][2];assert checked['latitude']==-7.25 and checked['longitude']==112.75 and checked['accuracy_m']==20
            assert 'gps_exception_reason' not in checked
            page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Laporan',exact=True).click()
            expect(page.get_by_role('heading',name='Laporan Utama',exact=True)).to_have_count(2)
            page.get_by_label('Nama PIC',exact=True).fill('PIC QA')
            page.get_by_label('Koneksi backbone').select_option('both')
            page.get_by_label('Ringkasan / hasil pemeriksaan').fill('Ringkasan QA '+PAYLOAD)
            page.get_by_label('Hasil pekerjaan',exact=True).select_option('pending')
            page.get_by_label('Alasan pekerjaan pending').fill('Menunggu tindak lanjut')
            page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Sampling',exact=True).click()
            expect(page.locator('.floor-points button')).to_have_count(4)
            page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Laporan',exact=True).click()
            expect(page.get_by_label('Ringkasan / hasil pemeriksaan')).to_have_value('Ringkasan QA '+PAYLOAD)
            page.get_by_role('button',name='Simpan laporan ke server').click()
            expect(page.get_by_role('status').filter(has_text='Laporan tersimpan di server')).to_be_visible()
            saved=writes[-1][2];assert saved['expected_version']==2 and saved['report']['fo']['speedtest_mbps']==0
            assert saved['report']['wireless']['tx_mbps']==30 and saved['report']['lan_notes']=='Catatan format lama'
            page.get_by_label('Nama PIC',exact=True).fill('PIC draf konflik')
            conflict[0]=True;page.get_by_role('button',name='Simpan laporan ke server').click()
            expect(page.get_by_role('alert')).to_contain_text('Data server berubah')
            expect(page.get_by_label('Nama PIC',exact=True)).to_have_value('PIC draf konflik')
            page.locator('.app-content').evaluate('el=>el.scrollTop=0')
            assert_navigation_clearance()
            page.screenshot(path=str(ARTIFACTS/'sync-conflict-390.png'),full_page=True)
            conflict[0]=False
            # Tab/radio screens never create measurements or change server completion.
            page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Sampling',exact=True).click()
            page.locator('.floor-points button').first.click()
            expect(page.get_by_role('heading',name='Connected Network')).to_be_visible()
            expect(page.locator('.network-grid')).not_to_contain_text('Koridor QA')
            for label in ('2.4 GHz','5 GHz'):page.get_by_role('button',name=label,exact=True).click()
            page.get_by_role('tab',name='Speedtest',exact=True).click()
            expect(page.get_by_role('button',name='Mulai Speedtest · Belum tersedia')).to_be_disabled()
            page.get_by_role('tab',name='Foto & Catatan',exact=True).click()
            expect(page.locator('.sampling-notes .card-title h2')).to_have_text(['Kondisi & Temuan','Tindakan & Rekomendasi','Dokumentasi Foto'])
            expect(page.locator('.sync-panel')).to_have_count(1)
            expect(page.locator('.sync-panel details')).not_to_have_attribute('open','')
            expect(page.locator('.sync-panel [role=alert]')).to_contain_text('Data server berubah')
            page.locator('.sync-panel summary').click()
            expect(page.locator('.sync-panel-details')).to_contain_text('Tidak ada sinkronisasi otomatis')
            page.locator('.sync-panel summary').click()
            expect(page.locator('.sync-panel [role=alert]')).to_be_visible()
            ctx.set_offline(True)
            expect(page.locator('.connection')).to_contain_text('Offline')
            note='</textarea>'+PAYLOAD
            page.get_by_label('Catatan teknisi',exact=True).fill(note)
            page.get_by_label('Temuan',exact=True).fill('Temuan lokal QA')
            page.get_by_label('Status titik lokal').select_option('good')
            photo=io.BytesIO();Image.new('RGB',(80,60),(14,115,86)).save(photo,'PNG')
            page.get_by_label('Pilih foto dari perangkat').set_input_files({'name':'fixture.png','mimeType':'image/png','buffer':photo.getvalue()})
            expect(page.locator('.photo-grid img')).to_have_count(1)
            page.get_by_role('tab',name='Wi-Fi Analyzer',exact=True).click();page.get_by_role('tab',name='Foto & Catatan',exact=True).click()
            expect(page.get_by_label('Catatan teknisi',exact=True)).to_have_value(note)
            assert page.locator('script:not([src]),img[src=x]').count()==0
            assert page.evaluate('window.xss') is None
            for width in (360,390,430,768):
                page.set_viewport_size({'width':width,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),('notes',width)
                assert page.locator('.app-content').evaluate('el=>el.scrollWidth<=el.clientWidth'),width
                assert_navigation_clearance()
                # Scroll/focus every field and photo action; their hit targets stay above the nav.
                for control in page.locator('.sampling-notes input,.sampling-notes select,.sampling-notes textarea,.sampling-notes button').all():
                    control.scroll_into_view_if_needed()
                    control.focus()
                    rect=control.bounding_box();nav=page.locator('.bottom-nav').bounding_box()
                    assert rect['y']+rect['height']<=nav['y']+1,(width,rect,nav)
                page.locator('.app-content').evaluate('el=>el.scrollTop=el.scrollHeight')
                assert_navigation_clearance()
                assert page.locator('.photo-grid').evaluate("el=>getComputedStyle(el).gridTemplateColumns.split(' ').length")==2
            page.set_viewport_size({'width':390,'height':844})
            screenshot_section('Kondisi & Temuan','sampling-notes-390.png')
            screenshot_section('Tindakan & Rekomendasi','sampling-actions-390.png')
            screenshot_section('Dokumentasi Foto','sampling-photos-390.png')
            # Short viewport simulates reduced space while the software keyboard is open.
            page.set_viewport_size({'width':390,'height':500})
            control=page.get_by_label('Keterangan foto',exact=True)
            control.scroll_into_view_if_needed();control.focus()
            assert_navigation_clearance()
            rect=control.bounding_box();nav=page.locator('.bottom-nav').bounding_box()
            assert rect['y']+rect['height']<=nav['y']+1
            page.set_viewport_size({'width':390,'height':844})
            # Leave and re-enter without discarding drafts; report errors visible offline.
            page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Review',exact=True).click()
            expect(page.get_by_role('heading',name='Persetujuan PIC')).to_be_visible()
            expect(page.locator('.review-point').first).to_contain_text('Belum selesai')
            expect(page.get_by_role('button',name='Submit / tanda tangan · Belum tersedia')).to_be_disabled()
            expect(page.locator('.app-content')).to_contain_text('Temuan lokal QA')
            expect(page.locator('.review-summary h3')).to_have_text(['Backbone Fiber Optic','Wireless Backbone','Local Area Network','Sampling Wi-Fi'])
            expect(page.locator('.review-summary article').first).to_contain_text('Hasil lama 0 Mbps')
            expect(page.locator('.review-summary article').nth(2)).to_contain_text('Belum diperiksa')
            expect(page.locator('.review-summary article').nth(3)).to_contain_text('0/4 titik selesai')
            page.locator('.review-summary').evaluate('el=>{const main=document.querySelector(".app-content");main.scrollTop+=el.getBoundingClientRect().top-main.getBoundingClientRect().top-12;}')
            assert_navigation_clearance()
            page.screenshot(path=str(ARTIFACTS/'review-390.png'),full_page=True)
            screenshot_section('Persetujuan PIC','review-pic-390.png')
            page.get_by_role('navigation',name='Navigasi utama').get_by_role('button',name='Beranda').click()
            ctx.set_offline(False);open_hotel()
            page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Laporan',exact=True).click()
            expect(page.get_by_label('Nama PIC',exact=True)).to_have_value('PIC draf konflik')
            page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Sampling',exact=True).click()
            page.locator('.floor-points button').first.click();page.get_by_role('tab',name='Foto & Catatan',exact=True).click()
            expect(page.get_by_label('Catatan teknisi',exact=True)).to_have_value(note);expect(page.locator('.photo-grid img')).to_have_count(1)
            # A real storage write failure must remain visibly flagged.
            page.evaluate("()=>{window.originalTransaction=IDBDatabase.prototype.transaction;IDBDatabase.prototype.transaction=function(names,mode,...rest){return window.originalTransaction.call(this,names,mode==='readwrite'?'readonly':mode,...rest);};}")
            page.get_by_label('Catatan teknisi',exact=True).fill('Gagal tulis fixture')
            expect(page.get_by_role('alert').first).to_contain_text('Gagal')
            page.evaluate('()=>{IDBDatabase.prototype.transaction=window.originalTransaction;}')
            page.get_by_label('Catatan teknisi',exact=True).fill(note)
            expect(page.get_by_role('status').filter(has_text='Draf lokal tersimpan')).to_be_visible()
            page.get_by_role('navigation',name='Navigasi utama').get_by_role('button',name='Profil').click()
            expect(page.locator('.badge').filter(has_text='3 perubahan lokal belum disinkronkan')).to_be_visible()
            # Expired auth clears session; token is never placed in IndexedDB/localStorage.
            expire[0]=True;page.get_by_role('navigation',name='Navigasi utama').get_by_role('button',name='Beranda').click();page.get_by_role('button',name='Muat ulang jadwal').click()
            expect(page.get_by_role('heading',name='Masuk ke aplikasi')).to_be_visible()
            assert page.evaluate('JSON.stringify({...localStorage,...sessionStorage})').find('fixture-token')==-1
            expire[0]=False;login();open_hotel()
            # XSS hotel and floor labels stay text; read-only approval disables edits.
            visit['site']['name']=PAYLOAD;visit['devices'][0]['floor']=PAYLOAD;visit['devices'][0]['point']=PAYLOAD
            visit['status']='approved'
            visit['version']+=1
            visit['report']['fo']={'download_mbps':0,'upload_mbps':0,'conformity':'not_conforming'}
            visit['report']['wireless']={'signal_dbm':-62}
            visit['report'].update(router_connector='normal',switch_connector='normal',signal_test='good',blank_spot=False,hotspot=False)
            page.get_by_role('button',name='Muat ulang kunjungan').click()
            expect(page.locator('.context-row')).to_contain_text(PAYLOAD)
            page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Laporan',exact=True).click()
            expect(page.get_by_label('Nama PIC',exact=True)).to_be_disabled()
            page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Review',exact=True).click()
            expect(page.locator('.review-summary article').first).to_contain_text('Tidak sesuai')
            expect(page.locator('.review-summary article').first).to_contain_text('↓ 0 Mbps')
            expect(page.locator('.review-summary article').nth(1)).to_contain_text('-62 dBm')
            expect(page.locator('.review-summary article').nth(2)).to_contain_text('5/5 item LAN tersimpan')
            expect(page.locator('.review-summary article').nth(2)).to_contain_text('Perlu perhatian')
            # Reloaded server version differs from the saved draft; conflict is visible while closed.
            expect(page.locator('.sync-panel [role=alert]').filter(has_text='Versi draf berbeda')).to_be_visible()
            page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Sampling',exact=True).click()
            expect(page.locator('.floor-card summary')).to_contain_text(PAYLOAD)
            assert page.locator('.app-content img[src=x],.app-content script').count()==0
            page.get_by_role('navigation',name='Navigasi utama').get_by_role('button',name='Profil').click()
            expect(page.get_by_role('heading',name='Data teknisi')).to_be_visible()
            page.get_by_role('button',name='Logout',exact=True).click()
            expect(page.get_by_role('heading',name='Masuk ke aplikasi')).to_be_visible()
            # A second technician cannot see the first account's local drafts/photos.
            USER['id']='second-tech';USER['name']='Teknisi Kedua';visit['technician_id']=USER['id'];visit['status']='assigned'
            ctx.clear_permissions()
            login();open_hotel()
            page.get_by_role('button',name='Check-in dengan GPS',exact=True).click()
            expect(page.get_by_role('alert')).to_be_visible(timeout=20000)
            page.get_by_text('GPS tidak tersedia?',exact=True).click()
            page.get_by_label('Alasan pengecualian GPS').fill('Izin lokasi ditolak · fixture QA')
            page.get_by_role('button',name='Check-in dengan alasan',exact=True).click()
            expect(page.get_by_role('status').filter(has_text='Check-in tersimpan')).to_be_visible()
            checked=writes[-1][2];assert checked['gps_exception_reason']=='Izin lokasi ditolak · fixture QA'
            assert 'latitude' not in checked and 'longitude' not in checked
            page.get_by_role('navigation',name='Tahap maintenance').get_by_role('button',name='Sampling',exact=True).click()
            page.locator('.floor-points button').first.click();page.get_by_role('tab',name='Foto & Catatan',exact=True).click()
            expect(page.get_by_label('Catatan teknisi',exact=True)).to_have_value('')
            expect(page.locator('.photo-grid img')).to_have_count(0)
            page.get_by_role('navigation',name='Navigasi utama').get_by_role('button',name='Profil').click()
            page.get_by_role('button',name='Logout',exact=True).click()
            # Empty schedule remains explicit.
            empty[0]=True
            login();expect(page.get_by_role('heading',name='Belum ada penugasan')).to_be_visible()
            assert not errors,errors
            assert not api_errors,api_errors
            assert all(path.endswith(('/check-in','/report')) for _,path,_ in writes),writes
            browser.close()
            print('Phase 3 browser passed: login/errors, schedules, GPS, Nusanet save/legacy/409, offline drafts/photos, storage failure, XSS, read-only, review/PIC, logout/401, responsive 360/390/430/768, screenshots. Fixture API only.')
    finally:server.shutdown();server.server_close()

if __name__=='__main__':run()
