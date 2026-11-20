"""Phase B UI/IndexedDB tests; static server + explicit fixtures, no DB or migrations."""
import io
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[2]
ARTIFACTS=ROOT/'artifacts/sampling'
VISIT={
    'id':'test-visit','hotel_id':'test-hotel','technician_id':'test-tech','status':'in_progress',
    'version':1,'planned_date':'2026-11-12','report':{},'site':{'name':'Hotel QA (fixture)','maintenance_profile':{}},
    'devices':[{'id':'test-ap','device_id':'test-device','floor':'26','point':'Area QA',
       'device':{'id':'test-device','name':'AP QA (fixture)','device_type':'ap'},'photos':[],
       'result':{'outcome':'pass','band_24':{'status':'measured','signal_dbm':-62,'channel':6,'bandwidth_mbps':0,'source':'manual'}},
       'speedtests':[{'id':'test-speed','band':'band_24','status':'completed',
          'created_at':'2026-11-12T10:00:00Z','finished_at':'2026-11-12T10:00:20Z',
          'context':{'transport':'diagnostic_tunnel_or_local','endpoint_origin':'http://fixture.test'},
          'metrics':{'download_mbps':18.5,'upload_mbps':7.2,'ping_ms':12,'jitter_ms':1.2}}]}]
}

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self,path):
        if path=='/':path='/index.html'
        if path.startswith('/assets/'):path=path[len('/assets'):]
        return super().translate_path(path)
    def log_message(self,*args):pass


def run():
    ARTIFACTS.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'backend/app/web')))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    buffer=io.BytesIO();Image.new('RGB',(80,60),(20,90,150)).save(buffer,'PNG')
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':1000})
            page=context.new_page();errors=[];writes=[];fail_next=[False]
            page.on('pageerror',lambda error:errors.append(str(error)))
            def api_route(route):
                if fail_next[0]:
                    fail_next[0]=False;route.fulfill(status=503,content_type='application/json',body='{"detail":"Server QA tidak tersedia"}');return
                if route.request.method!='GET':writes.append(route.request.method+' '+route.request.url)
                route.fulfill(status=200,content_type='application/json',body=json.dumps(VISIT))
            page.route('**/hotel-visits/**',api_route)
            url=f'http://127.0.0.1:{server.server_port}'
            def boot(user='test-tech'):
                page.goto(url)
                page.evaluate('''({visit,user})=>{
                    state.user={id:user,name:'QA',role:'technician'};state.token='test-token';
                    state.hotelVisit=visit;state.data={hotels:[{id:visit.hotel_id,name:visit.site.name}],devices:[],users:[],hotelvisits:[visit],visits:[],templates:[],schedules:[]};
                    document.querySelector('#workspace').hidden=false;document.querySelector('#login-view').hidden=true;
                }''',{'visit':VISIT,'user':user})
                page.evaluate("openSampling('test-visit')")
                expect(page.locator('.sampling-app')).to_be_visible()
            boot()
            fail_next[0]=True;page.evaluate("openSampling('test-visit')")
            expect(page.locator('.sampling-app [role=alert]')).to_contain_text('Server QA tidak tersedia')
            page.get_by_role('button',name='Coba lagi',exact=True).click()
            expect(page.locator('[data-sampling-floor]')).to_have_count(1)
            # Unit checks on measurement mapping and missing/zero values, no synthetic radio values.
            assert page.evaluate('samplingMetrics(null).download') is None
            assert page.evaluate("samplingMetrics({result:{band_24:{status:'not_tested',signal_dbm:-1,bandwidth_mbps:100}}}).signal") is None
            assert page.evaluate("samplingMetrics({result:{band_24:{status:'measured',signal_dbm:0,bandwidth_mbps:0}}}).download")==0
            assert page.evaluate('(async()=>!(await SamplingServices.scan()).available)()')
            assert page.evaluate('(async()=>!(await SamplingServices.connection()).available)()')
            assert page.locator('[data-sampling-floor]').count()==1
            expect(page.locator('.v2-stats')).to_contain_text('4')
            page.screenshot(path=str(ARTIFACTS/'dashboard-desktop.png'),full_page=True)
            page.locator('.v2-floor summary').first.click()
            page.locator('[data-sampling-floor]').click()
            expect(page.locator('.sampling-point-metrics').first).to_contain_text('-62')
            expect(page.locator('.sampling-point-metrics').first).to_contain_text('18.5')
            expect(page.locator('.sampling-point-metrics').nth(1)).to_contain_text('Belum diuji')
            page.locator('[data-sampling-point]').first.click()
            expect(page.get_by_role('heading',name='Jaringan Wi-Fi aktif')).to_be_visible()
            expect(page.locator('.sampling-network')).to_contain_text('Belum tersedia')
            assert page.locator('.sampling-network dd').all_text_contents()==['Belum tersedia']*11
            page.get_by_role('button',name='5 GHz',exact=True).click()
            expect(page.locator('#sampling-panel')).to_contain_text('estimasi')
            page.screenshot(path=str(ARTIFACTS/'analyzer-desktop.png'),full_page=True)
            page.get_by_role('tab',name='Speedtest',exact=True).click()
            expect(page.locator('.sampling-run')).to_contain_text('18.5')
            expect(page.locator('.sampling-run')).to_contain_text('Diagnostik tunnel/lokal')
            expect(page.locator('.sampling-run')).to_contain_text('http://fixture.test')
            # Native denied/unavailable path does not ask for browser location or fabricate SSID.
            assert not page.locator('.sampling-network').inner_text().count('AP QA')
            page.get_by_role('button',name='Mulai Speedtest',exact=True).click()
            expect(page.locator('#speed-dialog')).to_be_visible()
            expect(page.locator('#speed-dialog')).to_contain_text('belum dapat memastikan SSID/BSSID')
            page.locator('#speed-close').click()
            expect(page.get_by_role('tab',name='Speedtest',exact=True)).to_have_attribute('aria-selected','true')
            page.get_by_role('tab',name='Foto & Catatan',exact=True).click()
            page.locator('[data-sampling-note=notes]').fill('Draf teknisi <script>aman</script>')
            page.locator('[data-sampling-note=findings]').fill('Temuan QA')
            page.locator('[data-sampling-note=status]').select_option('attention')
            expect(page.locator('#sampling-feedback')).to_contain_text('Draf tersimpan')
            page.get_by_role('tab',name='Wi-Fi Analyzer',exact=True).click()
            page.get_by_role('tab',name='Foto & Catatan',exact=True).click()
            expect(page.locator('[data-sampling-note=notes]')).to_have_value('Draf teknisi <script>aman</script>')
            # Camera fallback persists Blob + category + caption locally, including offline.
            context.set_offline(True)
            expect(page.locator('#sampling-connectivity')).to_contain_text('Offline')
            page.locator('#sampling-photo-category').select_option(label='Foto area sampling')
            page.locator('#sampling-photo-caption').fill('Dokumentasi QA')
            page.locator('#sampling-photo-file').set_input_files({'name':'qa.png','mimeType':'image/png','buffer':buffer.getvalue()})
            expect(page.locator('[data-sampling-image]')).to_have_count(1)
            expect(page.locator('[data-sampling-image]')).to_have_attribute('src',__import__('re').compile('^blob:'))
            page.locator('[data-sampling-photo]').click();expect(page.locator('#sampling-photo-dialog')).to_be_visible()
            page.get_by_role('button',name='Tutup foto',exact=True).click()
            page.once('dialog',lambda dialog:dialog.dismiss());page.locator('[data-sampling-delete]').click()
            expect(page.locator('[data-sampling-image]')).to_have_count(1)
            page.locator('[data-sampling-note=action]').fill('Tindakan offline')
            expect(page.locator('#sampling-feedback')).to_contain_text('Draf tersimpan')
            page.get_by_role('tab',name='Speedtest',exact=True).click()
            expect(page.get_by_role('button',name='Mulai Speedtest',exact=True)).to_be_disabled()
            page.get_by_role('tab',name='Foto & Catatan',exact=True).click()
            for width in (360,390,768,1440):
                page.set_viewport_size({'width':width,'height':900})
                assert page.locator('.sampling-app').evaluate('(el)=>el.scrollWidth<=el.clientWidth')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert page.locator('.sampling-photo-grid').evaluate('(el)=>getComputedStyle(el).gridTemplateColumns.split(" ").length')==2
                if width==390:page.screenshot(path=str(ARTIFACTS/'notes-offline-mobile.png'),full_page=True)
            context.set_offline(False);boot()
            page.locator('.v2-floor summary').first.click()
            page.locator('[data-sampling-floor]').click();page.locator('[data-sampling-point]').first.click()
            page.get_by_role('tab',name='Foto & Catatan',exact=True).click()
            expect(page.locator('[data-sampling-note=action]')).to_have_value('Tindakan offline')
            expect(page.locator('[data-sampling-image]')).to_have_count(1)
            expect(page.locator('.sampling-photo-grid')).to_contain_text('Foto area sampling')
            expect(page.locator('.sampling-photo-grid')).to_contain_text('Dokumentasi QA')
            page.once('dialog',lambda dialog:dialog.accept());page.locator('[data-sampling-delete]').click()
            expect(page.locator('[data-sampling-image]')).to_have_count(0)
            # Quota/blocked write failure must not show success; recover on next edit.
            # Object is frozen: induce a real IndexedDB read-only failure via transaction shim.
            page.evaluate('''()=>{window.originalTransaction=IDBDatabase.prototype.transaction;
                IDBDatabase.prototype.transaction=function(names,mode,...rest){return originalTransaction.call(this,names,mode==='readwrite'?'readonly':mode,...rest);};}''')
            page.locator('[data-sampling-note=notes]').fill('Write should fail')
            expect(page.locator('#sampling-feedback')).to_have_class(__import__('re').compile('sampling-error'))
            expect(page.locator('#sampling-sync-label')).to_have_text('Gagal menyimpan perubahan')
            expect(page.locator('#sampling-feedback')).to_be_visible()
            expect(page.locator('#sampling-feedback')).to_have_attribute('role','alert')
            page.evaluate('renderSampling()')
            expect(page.locator('#sampling-feedback')).to_be_visible()
            page.evaluate('()=>{IDBDatabase.prototype.transaction=originalTransaction;}')
            page.locator('[data-sampling-note=notes]').fill('Write recovered')
            expect(page.locator('#sampling-feedback')).to_contain_text('Draf tersimpan')
            # Target configuration defaults to four and is persisted separately from report data.
            page.locator('[data-sampling-back]').click();page.locator('[data-sampling-back]').click()
            page.evaluate("openHotelDetail('test-hotel','floors')")
            page.locator('#hotel-add-floor [name=floor]').fill('27')
            expect(page.locator('#hotel-add-floor [name=target]')).to_have_value('2')
            page.locator('#hotel-add-floor button').click()
            expect(page.locator('.hotel-grid')).to_contain_text('Lantai 27')
            page.evaluate("openSampling('test-visit')")
            expect(page.locator('[data-sampling-floor]')).to_have_count(2)
            page.locator('.v2-floor summary').last.click()
            page.locator('[data-sampling-floor]').last.click()
            expect(page.locator('[data-sampling-point]')).to_have_count(4)
            page.locator('[data-sampling-point]').last.click();page.get_by_role('tab',name='Foto & Catatan',exact=True).click()
            page.locator('[data-sampling-note=location]').fill('Lokasi ditentukan QA')
            expect(page.locator('#sampling-feedback')).to_contain_text('Draf tersimpan')
            page.locator('[data-sampling-back]').click()
            page.evaluate("openHotelDetail('test-hotel','floors')")
            target=page.locator('.hotel-grid .card').filter(has=page.get_by_role('heading',name='Lantai 27',exact=True)).locator('[data-floor-config]')
            target.locator('[name=target]').fill('1');target.locator('button').click()
            expect(target.locator('[name=target]')).to_have_value('1')
            page.evaluate("openSampling('test-visit')")
            page.locator('.v2-floor summary').last.click();page.locator('[data-sampling-floor]').last.click()
            expect(page.locator('[data-sampling-point]')).to_have_count(4)
            boot();expect(page.locator('[data-sampling-floor]')).to_have_count(2)
            page.locator('.v2-floor summary').last.click()
            page.locator('[data-sampling-floor]').last.click();expect(page.locator('[data-sampling-point]')).to_have_count(4)
            # Account isolation and read-only state.
            boot('another-tech');expect(page.locator('[data-sampling-floor]')).to_have_count(1)
            assert page.locator('#sampling-add-floor').count()==0
            page.locator('.v2-floor summary').first.click()
            page.locator('[data-sampling-floor]').click();page.locator('[data-sampling-point]').first.click()
            page.get_by_role('tab',name='Foto & Catatan',exact=True).click()
            expect(page.locator('[data-sampling-note=notes]')).to_have_value('')
            expect(page.locator('[data-sampling-note=notes]')).to_be_disabled()
            # Main report's approved fields still render; sampling never writes API data.
            boot();page.evaluate('editHotelReport()')
            expect(page.locator('#dialog-fields [name=router_connector]')).to_be_visible()
            expect(page.locator('#dialog-fields [name=fo_download]')).to_have_count(1)
            page.locator('#cancel-dialog').click()
            assert writes==[],writes
            assert errors==[],errors
            browser.close()
            print('Sampling UI passed: unit mapping, 360/390/768/1440px, tabs, native unavailable, offline IndexedDB notes/photos, reload, delete confirmation, storage errors, floor targets, account isolation, error/retry, protected report; no API writes/migrations.')
    finally:
        server.shutdown();server.server_close()

if __name__=='__main__':run()
