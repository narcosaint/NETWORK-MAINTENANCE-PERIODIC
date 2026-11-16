"""Phase 2 browser regression. Static assets + intercepted fixtures only; no DB."""
import copy
import json
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from hotel_navigation_ui import COLLECTIONS
from sampling_ui import Handler, VISIT

ROOT=Path(__file__).resolve().parents[2]
ARTIFACTS=ROOT/'artifacts/phase2-1'

def run():
    ARTIFACTS.mkdir(parents=True,exist_ok=True)
    visit=copy.deepcopy(VISIT)
    run=visit['devices'][0]['speedtests'][0]
    run['context'].update(transport='direct_https',network='hotel_wifi',wifi_confirmed=True)
    visit['devices'][0]['photos']=[{'id':'qa-photo'}]
    visit['devices'][0]['point']='Kamar QA <script>'
    data=copy.deepcopy(COLLECTIONS);data['hotelvisits']=[visit]
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'backend/app/web')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1050})
            errors=[];writes=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            def api(route):
                if route.request.method!='GET':writes.append(route.request.method)
                route.fulfill(status=200,content_type='application/json',body=json.dumps([] if '/history?' in route.request.url else visit))
            page.route('**/hotel-visits/**',api)
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.evaluate('''data=>{state.token='fixture';state.user={id:'test-tech',name:'QA',role:'technician'};state.data=data;document.querySelector('#workspace').hidden=false;document.querySelector('#login-view').hidden=true;}''',data)
            page.evaluate("openSampling('test-visit')")
            expect(page.locator('.v2-dashboard')).to_be_visible()
            expect(page.locator('.v2-progress')).to_contain_text('1/4 titik selesai')
            expect(page.locator('.v2-stats .v2-stat').nth(3)).to_contain_text('0')
            page.locator('.v2-floor summary').click()
            expect(page.locator('.v2-metrics')).to_contain_text('18.5 Mbps')
            expect(page.locator('.v2-point-list')).to_contain_text('Kamar QA <script>')
            assert page.locator('.v2-dashboard script').count()==0
            # Local status cannot upgrade server completion; diagnostics/manual cannot count.
            assert page.evaluate("v2Evidence({item:{result:{outcome:'pass'},photos:[{}],speedtests:[]}}).done")==False
            assert page.evaluate("v2Evidence({item:{result:{outcome:'pass'},photos:[{}],speedtests:[{status:'completed',metrics:{download_mbps:100},context:{transport:'diagnostic_tunnel_or_local'}}]}}).done")==False
            assert page.evaluate("v2Evidence({item:{result:{outcome:'fail'},photos:[{}],speedtests:[{status:'failed',error:'Tidak ada koneksi'}]}}).done")==True
            assert page.evaluate("v2Evidence({item:{result:{outcome:'fail'},photos:[{}],speedtests:[{status:'failed',error:' '}]}}).done")==False
            page.evaluate("samplingView.drafts['local:server:26:0']={status:'good'};renderSampling()")
            expect(page.locator('.v2-progress')).to_contain_text('1/4 titik selesai')
            # Screenshot one actual-data fixture, with no synthetic charts or network claims.
            for width in (1440,768,430,390,360):
                page.set_viewport_size({'width':width,'height':1050})
                if not page.locator('.v2-floor').get_attribute('open')=='' :
                    page.locator('.v2-floor summary').click()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                if width in (1440,390):
                    page.screenshot(path=str(ARTIFACTS/f'dashboard-{width}.png'),full_page=True)
            # Compact disclosure, missing/zero values and actual section states.
            expect(page.locator('#sampling-sync-label')).to_have_text('Perubahan belum disinkronkan')
            expect(page.locator('.v21-inspections article')).to_have_count(4)
            expect(page.locator('.v21-inspections article').first).to_contain_text('Belum diperiksa')
            assert page.evaluate("v21Backbone({fo:{notes:'catatan',download_mbps:null}},'fo').label")=='Belum diperiksa'
            assert page.evaluate("v21Backbone({fo:{download_mbps:0,conformity:'not_conforming'}},'fo').label")=='Tidak sesuai'
            assert page.evaluate("v21Backbone({wireless:{signal_dbm:-61}},'wireless').label")=='Pengukuran tersimpan'
            assert page.locator('#sampling-add-floor,#sampling-target').count()==0
            # Drawer exposes every allowed menu on narrow screens and closes on Escape/selection.
            for width in (360,390,430):
                page.set_viewport_size({'width':width,'height':850})
                page.locator('#open-navigation').click()
                expect(page.locator('#open-navigation')).to_have_attribute('aria-expanded','true')
                for button in page.locator('#navigation button').all():
                    expect(button).to_be_visible()
                    box=button.bounding_box();assert box['x']>=0 and box['x']+box['width']<=width
                page.locator('#close-navigation').press('Escape')
                expect(page.locator('#open-navigation')).to_have_attribute('aria-expanded','false')
            page.set_viewport_size({'width':1440,'height':1050})
            # Existing Nusanet form stays accessible and editable without touching the API.
            page.locator('[data-sampling-report]').click()
            page.locator('[data-hotel-report]').click()
            expect(page.locator('#form-dialog')).to_be_visible()
            expect(page.locator('#dialog-fields')).to_contain_text('LOCAL AREA NETWORK')
            expect(page.locator('#dialog-fields')).to_contain_text('Keterangan')
            # Required browser fields and business validation remain active.
            page.locator('#dialog-fields [name=pic_name]').fill('PIC QA')
            page.locator('#dialog-fields [name=backbone_mode]').select_option('both')
            for key,value in [('router_connector','normal'),('switch_connector','normal'),('signal_test','good'),('blank_spot','false'),('hotspot','true')]:
                page.locator(f'#dialog-fields [name={key}]').select_option(value)
                page.locator(f'#dialog-fields [name={key}_notes]').fill('Keterangan QA')
            page.locator('#dialog-fields [name=summary]').fill('Laporan QA')
            page.locator('#dialog-fields [name=pic_exception_reason]').fill('PIC belum menandatangani')
            page.locator('#dialog-fields [name=work_status]').select_option('pending')
            page.locator('#save-form').click()
            expect(page.locator('#form-error')).to_contain_text('Isi alasan pekerjaan pending')
            assert not writes
            # Execute the unchanged form action against an intercepted save endpoint.
            page.locator('#dialog-fields [name=pending_reason]').fill('Menunggu tindak lanjut')
            page.route('**/hotel-visits/test-visit/report',lambda route:(writes.append(route.request.post_data_json),route.fulfill(status=200,content_type='application/json',body=json.dumps(visit))))
            page.evaluate("editorAction(new FormData(document.querySelector('#editor-form')))")
            assert len(writes)==1
            saved=writes.pop()
            assert saved['expected_version']==1
            assert saved['report']['summary']=='Laporan QA'
            assert saved['report']['router_connector_notes']=='Keterangan QA'
            assert saved['report']['fo'] is not None and saved['report']['wireless'] is not None
            page.locator('#cancel-dialog').click()
            # XSS fixtures remain local: hotel/floor/point/notes are text, never executable nodes.
            page.evaluate("openSampling('test-visit')")
            payload='<img src=x onerror="window.xssExecuted=true"><script>window.xssExecuted=true</script>'
            page.evaluate("""payload=>{
                window.xssExecuted=false;samplingView.visit.site.name=payload;
                samplingView.visit.devices[0].floor=payload;samplingView.visit.devices[0].point=payload;
                samplingView.floor=null;samplingView.point=null;renderSampling();
            }""",payload)
            expect(page.locator('.v2-title')).to_contain_text(payload)
            expect(page.locator('.v2-floor summary')).to_contain_text(payload)
            assert page.locator('.v2-dashboard img,.v2-dashboard script').count()==0
            page.locator('.v2-floor summary').click();page.locator('[data-sampling-floor]').click()
            page.locator('[data-sampling-point]').first.click()
            page.get_by_role('tab',name='Foto & Catatan',exact=True).click()
            note='</textarea>'+payload
            page.locator('[data-sampling-note=notes]').fill(note)
            expect(page.locator('#sampling-feedback')).to_contain_text('Draf tersimpan')
            page.get_by_role('tab',name='Wi-Fi Analyzer',exact=True).click()
            page.get_by_role('tab',name='Foto & Catatan',exact=True).click()
            expect(page.locator('[data-sampling-note=notes]')).to_have_value(note)
            assert page.locator('.sampling-app script,.sampling-app img[src=x]').count()==0
            assert page.evaluate('window.xssExecuted') is False
            # No-data state and failed fetch must not show fabricated totals.
            visit['devices']=[]
            page.evaluate("openSampling('test-visit')")
            expect(page.locator('.v2-stats')).to_contain_text('Belum tersedia')
            assert not writes,writes
            assert not errors,errors
            browser.close()
            print('Dashboard V2 passed: actual evidence, local exclusion, failures, disclosures, Nusanet form, responsive 360/390/768/1440, screenshots; no API writes.')
    finally:
        server.shutdown();server.server_close()

if __name__=='__main__':run()
