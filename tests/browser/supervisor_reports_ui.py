"""Interactive supervisor summary/results; fixture data only, no production writes."""
import copy,json,threading
from pathlib import Path
from functools import partial
from datetime import date
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright,expect
from sampling_ui import Handler,VISIT
from hotel_navigation_ui import COLLECTIONS
ROOT=Path(__file__).resolve().parents[2]

def run():
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'backend/app/web')))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];writes=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   period=date.today().isoformat()[:7]
   definitions=[('in_progress','completed','Pembersihan selesai; draf',False),('submitted','pending','Menunggu sparepart',False),('revision_requested','completed','Perbaikan perlu revisi',False),('approved','completed','Pekerjaan selesai disetujui',True),('approved','pending','Approved tetapi pending',False),('assigned',None,'',False)]
   visits=[]
   for index,(status,work,summary,done) in enumerate(definitions):
    v=copy.deepcopy(VISIT);v.update(id='qa-result-'+str(index),planned_date=period+'-12',status=status,maintenance_completed=done)
    v['report'].update(summary=summary,work_status=work,pending_reason='Menunggu sparepart' if work=='pending' else None)
    visits.append(v)
   data=copy.deepcopy(COLLECTIONS);data['hotelvisits']=visits
   def bridge(route):
    if route.request.method!='GET':writes.append(route.request.method)
    path=urlsplit(route.request.url).path
    value=[] if path.endswith('/history') else next((v for v in visits if path.endswith('/'+v['id'])),None)
    route.fulfill(status=200,content_type='application/json',body=json.dumps(value))
   page.route('**/hotel-visits/**',bridge)
   page.goto(f'http://127.0.0.1:{server.server_port}')
   page.evaluate('''data=>{state.user={id:'admin',name:'QA Supervisor',role:'supervisor'};state.token='qa';state.data=data;state.page='dashboard';document.querySelector('#workspace').hidden=false;document.querySelector('#login-view').hidden=true;render();}''',data)
   expect(page.locator('.stats button')).to_have_count(6)
   expect(page.locator('.work-charts')).to_be_visible()
   page.locator('.stats [data-page=hotels]').click();assert page.evaluate('state.page')=='hotels'
   page.evaluate("navigate('dashboard')")
   page.locator('.stats [data-results-filter=done]').click()
   expect(page.get_by_role('heading',name='Hasil Maintenance',exact=True)).to_be_visible()
   expect(page.locator('.table-wrap tbody tr')).to_have_count(1)
   expect(page.locator('.table-wrap')).to_contain_text('Pekerjaan selesai disetujui')
   page.locator('[data-results-reset]').click();expect(page.locator('.table-wrap tbody tr')).to_have_count(6)
   page.locator('#results-status').select_option('work_pending');expect(page.locator('.table-wrap tbody tr')).to_have_count(2)
   page.locator('#results-search').fill('Approved tetapi');expect(page.locator('.table-wrap tbody tr')).to_have_count(1)
   page.locator('[data-results-reset]').click()
   page.locator('#results-hotel').select_option('other-hotel');expect(page.get_by_role('heading',name='Tidak ada laporan yang sesuai.',exact=True)).to_be_visible()
   page.locator('[data-results-reset]').click()
   page.locator('[data-result-visit=qa-result-0]').click()
   expect(page.locator('#page-content')).to_contain_text('Pembersihan selesai; draf')
   expect(page.locator('#breadcrumb')).to_contain_text('Hasil Maintenance')
   page.get_by_role('button',name='← Daftar hasil maintenance',exact=True).click()
   expect(page.get_by_role('heading',name='Hasil Maintenance',exact=True)).to_be_visible()
   page.evaluate("navigate('dashboard')")
   page.locator('.work-status-chart [data-results-filter=submitted]').click()
   expect(page.locator('.table-wrap tbody tr')).to_have_count(1)
   expect(page.locator('.table-wrap')).to_contain_text('Menunggu sparepart')
   page.locator('[data-results-reset]').click()
   for width in (360,390,768,1440):
    page.set_viewport_size({'width':width,'height':950})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
   page.evaluate("navigate('dashboard')")
   page.locator('.work-month-chart button').last.click()
   expect(page.locator('#results-period')).to_have_value(period)
   dest=ROOT/'artifacts/supervisor';dest.mkdir(parents=True,exist_ok=True)
   page.set_viewport_size({'width':1440,'height':1050});page.screenshot(path=str(dest/'hasil-maintenance.png'),full_page=True)
   page.evaluate("state.user.role='technician';navigate('dashboard')")
   expect(page.locator('#navigation [data-page=reports]')).to_have_count(0)
   assert not errors,errors
   assert not writes,writes
   browser.close()
   print('PASS supervisor results: clickable counts, truthful status/trend charts, filters/search, draft/pending/approved distinction, detail/back, role navigation, responsive; no production writes')
 finally:server.shutdown();server.server_close()
if __name__=='__main__':run()
