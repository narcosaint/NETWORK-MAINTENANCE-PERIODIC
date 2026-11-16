"""Hotel-first navigation checks against fixtures; never write production data."""
import json
import os
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from sampling_ui import Handler, VISIT

ROOT = Path(__file__).resolve().parents[2]
HOTELS = [{'id':'test-hotel','name':'Hotel QA (fixture)','address':'Alamat QA'},
          {'id':'other-hotel','name':'Hotel Kedua (fixture)','address':''}]
DEVICES = [{'id':'test-device','hotel_id':'test-hotel','name':'AP QA (fixture)','device_type':'ap'},
           {'id':'other-device','hotel_id':'other-hotel','name':'AP hotel lain','device_type':'ap'}]
LEGACY = {'id':'legacy-visit','schedule_id':'legacy-schedule','technician_id':'test-tech','status':'approved','created_at':'2026-11-01'}
COLLECTIONS = {'hotels':HOTELS,'devices':DEVICES,'users':[{'id':'test-tech','name':'Teknisi QA','role':'technician','active':True}],
               'templates':[], 'schedules':[{'id':'legacy-schedule','device_id':'test-device','month':'2026-11-01'}],
               'visits':[LEGACY], 'hotelvisits':[VISIT]}

def run():
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'backend/app/web')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            page=browser.new_page(viewport={'width':1440,'height':1000})
            errors=[];writes=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            def visit_route(route):
                if route.request.method!='GET':writes.append(route.request.url)
                route.fulfill(status=200,content_type='application/json',body=json.dumps(VISIT))
            page.route('**/hotel-visits/**',visit_route)
            page.goto(os.environ.get('HOTEL_UI_TEST_ORIGIN',f'http://127.0.0.1:{server.server_port}'))
            def boot(role='supervisor'):
                page.evaluate('''({data,role})=>{
                    state.token='fixture-token';state.user={id:'test-tech',name:'QA',role};
                    state.data=data;state.page='dashboard';state.hotelVisit=null;state.visit=null;
                    hotelDetailView=null;clearSampling();document.querySelector('#workspace').hidden=false;
                    document.querySelector('#login-view').hidden=true;render();
                }''',{'data':COLLECTIONS,'role':role})
            boot()
            expect(page.locator('#navigation button')).to_have_text(['◫Ringkasan','▣Maintenance Hotel','▤Data Hotel','♙Tim Teknisi','☷Template Checklist'])
            page.locator('#navigation [data-page=hotels]').click()
            page.locator('[data-site-detail=test-hotel]').click()
            expect(page.get_by_role('tab')).to_have_text(['Informasi Hotel','Lantai','Perangkat','Titik Sampling','Riwayat Maintenance'])
            expect(page.locator('#navigation .active')).to_contain_text('Data Hotel')
            expect(page.locator('#breadcrumb')).to_contain_text('Data Hotel / Hotel QA (fixture) / Informasi Hotel')
            page.get_by_role('tab',name='Perangkat',exact=True).click()
            expect(page.locator('#hotel-detail-panel')).to_contain_text('AP QA (fixture)')
            expect(page.locator('#hotel-detail-panel')).not_to_contain_text('AP hotel lain')
            page.get_by_role('button',name='Tambah perangkat',exact=False).click()
            expect(page.locator('[name=hotel_id]')).to_have_value('test-hotel')
            page.locator('#cancel-dialog').click()
            page.get_by_role('tab',name='Riwayat Maintenance',exact=True).click()
            page.locator('.legacy-history summary').click()
            expect(page.locator('[data-visit=legacy-visit]')).to_be_visible()
            page.get_by_role('tab',name='Lantai',exact=True).click()
            page.locator('#hotel-add-floor [name=floor]').fill('27')
            expect(page.locator('#hotel-add-floor [name=target]')).to_have_value('4')
            page.locator('#hotel-add-floor button').click()
            expect(page.locator('.hotel-grid')).to_contain_text('Lantai 27')
            floor_card=page.locator('.hotel-grid .card').filter(has=page.get_by_role('heading',name='Lantai 27',exact=True))
            form=floor_card.locator('[data-floor-config]')
            form.locator('[name=target]').fill('6');form.locator('button').click()
            expect(page.locator('.hotel-grid')).to_contain_text('6 titik sampling · target 6')
            floor_card.get_by_role('button',name='Lihat titik sampling',exact=False).click()
            expect(page.locator('#hotel-detail-panel tbody tr')).to_have_count(6)
            page.get_by_role('tab',name='Titik Sampling',exact=True).press('ArrowRight')
            expect(page.get_by_role('tab',name='Riwayat Maintenance',exact=True)).to_have_attribute('aria-selected','true')
            # The sidebar root resets a selected hotel; history remains accessible.
            page.locator('#navigation [data-page=hotelvisits]').click()
            page.locator('[data-maintenance-hotel=test-hotel]').click()
            expect(page.locator('#breadcrumb')).to_contain_text('Maintenance Hotel / Hotel QA')
            page.locator('#maintenance-month').fill('2026-10')
            expect(page.locator('[data-maintenance-visit]')).to_have_count(0)
            page.locator('#maintenance-month').fill('2026-11')
            expect(page.locator('[data-maintenance-visit]')).to_have_count(1)
            page.locator('[data-hotel-create]').click()
            expect(page.locator('[name=hotel_id]')).to_have_value('test-hotel')
            expect(page.locator('[name=period]')).to_have_value('2026-11')
            page.locator('[name=technician_id]').select_option('test-tech')
            page.locator('[name=planned_date]').fill('2026-12-01')
            page.locator('#save-form').click()
            expect(page.locator('#form-error')).to_contain_text('Tanggal rencana harus berada')
            assert not writes
            page.locator('#cancel-dialog').click()
            page.locator('[data-maintenance-visit]').click()
            expect(page.locator('.sampling-app')).to_be_visible()
            expect(page.locator('#navigation .active')).to_contain_text('Maintenance Hotel')
            expect(page.locator('[data-sampling-floor]')).to_have_count(2)
            page.locator('.v2-floor summary').filter(has_text='Lantai 26').click()
            page.locator('[data-sampling-floor="server:26"]').click()
            page.locator('[data-sampling-point]').first.click()
            expect(page.locator('#breadcrumb')).to_contain_text('Lantai 26')
            expect(page.get_by_role('tab')).to_have_text(['Wi-Fi Analyzer','Speedtest','Foto & Catatan'])
            page.locator('[data-sampling-back]').click()
            expect(page.locator('[data-sampling-point]')).to_have_count(4)
            page.locator('[data-sampling-back]').click();page.locator('[data-sampling-back]').click()
            expect(page.locator('[data-maintenance-visit]')).to_have_count(1)
            page.locator('#breadcrumb [data-page=hotelvisits]').click()
            expect(page.locator('.hotel-grid .card')).to_have_count(2)
            # Every supervisor menu is reachable in the mobile drawer, including the last item.
            for width in (360,390,430):
                page.set_viewport_size({'width':width,'height':740})
                for key in ('dashboard','hotelvisits','hotels','users','templates'):
                    page.locator('#open-navigation').click()
                    page.locator(f'#navigation [data-page={key}]').click()
                    expect(page.locator('#open-navigation')).to_have_attribute('aria-expanded','false')
                    assert page.evaluate('state.page')==key
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,key)
                page.locator('#open-navigation').click()
                page.locator('#close-navigation').press('Shift+Tab')
                expect(page.locator('#logout')).to_be_focused()
                page.locator('#logout').press('Tab')
                expect(page.locator('#close-navigation')).to_be_focused()
                page.locator('#close-navigation').press('Escape')
            # No horizontal overflow in the new hotel pages.
            for width in (360,390,768,1440):
                page.set_viewport_size({'width':width,'height':950})
                page.evaluate("openHotelDetail('test-hotel','devices')")
                expect(page.locator('#hotel-detail-panel')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
            boot('technician')
            expect(page.locator('#navigation button')).to_have_count(4)
            expect(page.locator('#navigation')).not_to_contain_text('Tim Teknisi')
            page.evaluate("openHotelDetail('test-hotel','devices')")
            expect(page.locator('#hotel-detail-panel')).to_be_visible()
            expect(page.locator('[data-create=devices]')).to_have_count(0)
            expect(page.locator('[data-edit=devices]')).to_have_count(0)
            assert not errors,errors
            assert not writes,writes
            browser.close()
            print('Hotel navigation passed: sidebar roles, hotel-scoped inventory, monthly PM validation/filter, local floors/targets, legacy history, sampling flow, breadcrumbs/back, tabs/keyboard, responsive widths; no production writes.')
    finally:
        server.shutdown();server.server_close()

if __name__=='__main__':run()
