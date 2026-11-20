"""Hotel-wide visit UI against a disposable PostgreSQL database and private storage."""
import io
from PIL import Image
from playwright.sync_api import sync_playwright, expect


def run(base_url, password, artifacts):
    buffer=io.BytesIO();Image.new('RGB',(80,60),(40,100,60)).save(buffer,'PNG')
    photo={'name':'device.png','mimeType':'image/png','buffer':buffer.getvalue()}
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(viewport={'width':1440,'height':1000},locale='id-ID',
                    permissions=['geolocation'],geolocation={'latitude':-6.2,'longitude':106.8})
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        def login(username):
            page.goto(base_url);page.locator('[name=username]').fill(username);page.locator('[name=password]').fill(password)
            page.get_by_role('button',name='Masuk',exact=False).click();expect(page.locator('#workspace')).to_be_visible()
        def nav(name):page.locator('#navigation').get_by_role('button',name=name,exact=True).click()
        def click(name):page.get_by_role('button',name=name,exact=True).click()
        def field(name,value):page.locator('#dialog-fields [name='+name+']').fill(value)
        def choose(name,value):page.locator('#dialog-fields [name='+name+']').select_option(value)
        def save():
            page.locator('#editor-form button[type=submit]').click()
            expect(page.locator('#form-dialog')).not_to_be_visible()
        def card(name):return page.locator('article.card').filter(has=page.get_by_role('heading',name=name,exact=True))
        def check_layout(expected_count):
            items=page.locator('#dialog-fields .maintenance-item')
            expect(items).to_have_count(expected_count)
            for item in items.all():
                expect(item.locator('.maintenance-item-title')).to_have_count(1)
                assert item.locator('.maintenance-control > label').evaluate_all('(els)=>els.map(el=>Array.from(el.childNodes).filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join("").trim())')==['Status','Keterangan']
                expect(item.locator('select')).to_have_count(1)
                expect(item.locator('textarea')).to_have_count(1)
            for width in (390,768,1440):
                page.set_viewport_size({'width':width,'height':1000})
                columns=items.first.locator('.maintenance-item-fields').evaluate('(el)=>getComputedStyle(el).gridTemplateColumns.split(" ").length')
                assert columns==(1 if width<640 else 2), (width,columns)
                assert page.locator('#form-dialog').evaluate('(el)=>el.scrollWidth<=el.clientWidth')
            page.set_viewport_size({'width':1440,'height':1000})
        login('web_admin')
        nav('Hotel');click('＋ Tambah hotel');field('name','Hotel Uji Browser');field('address','Alamat khusus staging');field('customer_name','PT Pelanggan Uji');field('profile_percent','90');field('profile_fo_down','50');field('profile_fo_up','25');field('profile_wireless_down','30');field('profile_wireless_up','10');save()
        nav('Perangkat')
        for kind,name in [('router','Router Uji'),('switch','Switch Uji'),('ap','AP 2601'),('ap','AP Koridor')]:
            click('＋ Tambah perangkat');page.locator('[name=hotel_id]').select_option(label='Hotel Uji Browser')
            field('name',name);choose('device_type',kind);field('brand','Brand Uji');field('location','Lantai 26');save()
        nav('Tim');click('＋ Tambah tim');field('username','web_tech');field('name','Teknisi Uji');field('password',password);save()
        nav('Kunjungan hotel');click('＋ Jadwalkan kunjungan hotel')
        page.locator('[name=hotel_id]').select_option(label='Hotel Uji Browser')
        page.locator('[name=technician_id]').select_option(label='Teknisi Uji');field('planned_date','2026-11-12');save()
        expect(page.get_by_role('button',name='Buka laporan →')).to_be_visible()
        click('Keluar');login('web_tech');nav('Kunjungan hotel');click('Buka laporan →');click('Mulai pemeriksaan hotel');save()
        click('＋ Pilih AP sampling');page.locator('[name=device_id]').select_option(label='AP 2601 · Lantai 26')
        field('floor','26');field('point','Kamar 2601');save()
        expect(page.locator('article.card')).to_have_count(3)
        for name in ('Router Uji','Switch Uji','AP 2601'):
            card(name).get_by_role('button',name='Catat hasil & pengukuran AP' if name.startswith('AP') else 'Isi hasil pemeriksaan').click()
            check_layout(3 if name.startswith('AP') else 1)
            choose('outcome','pass');field('notes','Kondisi perangkat normal')
            if name.startswith('AP'):
                choose('b24_status','measured');field('b24_signal','-65');field('b24_channel','6');field('b24_speed','42.5')
                field('b24_ssid','Hotel Test');choose('b5_status','unavailable');field('b5_reason','AP hanya mendukung band 2.4 GHz')
            save()
        # Actual LibreSpeed worker traffic, throttled only in the disposable browser.
        cdp=context.new_cdp_session(page);cdp.send('Network.enable')
        cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':10,'downloadThroughput':2*1024*1024,'uploadThroughput':1024*1024})
        card('AP 2601').get_by_role('button',name='Jalankan speedtest').click()
        page.locator('#speed-dialog [name=band]').select_option('band_24')
        page.locator('#speed-dialog [name=network]').select_option('hotel_wifi')
        page.locator('#speed-dialog [name=wifi_confirmed]').check()
        page.get_by_role('button',name='Mulai pengukuran',exact=True).click()
        expect(page.locator('#speed-stage')).to_contain_text('Hasil pengukuran tersimpan',timeout=60000)
        expect(page.locator('#speed-stage')).to_contain_text('tidak dimasukkan')
        assert float(page.locator('#speed-dl').inner_text())>0
        assert float(page.locator('#speed-ul').inner_text())>0
        page.screenshot(path=str(artifacts/'automatic-speedtest.png'),full_page=True)
        page.get_by_role('button',name='Tutup',exact=True).click()
        expect(card('AP 2601')).to_contain_text('42.5 Mbps')
        expect(card('AP 2601')).to_contain_text('Diagnostik tunnel/lokal')
        card('AP 2601').get_by_role('button',name='Jalankan speedtest').click()
        page.locator('#speed-dialog [name=band]').select_option('band_24')
        page.locator('#speed-dialog [name=network]').select_option('unknown')
        page.get_by_role('button',name='Mulai pengukuran',exact=True).click()
        page.get_by_role('button',name='Batalkan pengujian',exact=True).click()
        expect(page.locator('#speed-stage')).to_contain_text('dibatalkan',timeout=10000)
        page.get_by_role('button',name='Tutup',exact=True).click()
        cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1})
        click('Isi laporan utama');field('pic_name','PIC Uji');choose('backbone_mode','failover')
        check_layout(5)
        assert page.locator('#dialog-fields .maintenance-item-title').all_text_contents()==['a. Koneksi LAN Router','b. LAN ke Switch','a. Signal Test','b. Blank Spot','c. Hotspot']
        assert page.locator('#dialog-fields .maintenance-category-title').all_text_contents()==['1. LAN','2. Wireless dan Hotspot']
        expect(page.locator('#report-customer-name')).to_have_text('PT Pelanggan Uji')
        assert page.locator('[name=customer_company]').count()==0
        assert page.locator('[name=fo_conformity]').count()==0
        assert page.locator('[name=wireless_tx]').count()==0
        assert page.locator('[name=wireless_ccq]').count()==0
        field('fo_download','46.5');field('fo_upload','24');expect(page.locator('#fo-comparison')).to_have_text('Sesuai')
        field('wireless_download','30.5');field('wireless_upload','8');field('wireless_signal','-60');field('wireless_linktest','Link test radio: 80 Mbps')
        expect(page.locator('#wireless-comparison')).to_have_text('Tidak sesuai')
        field('wireless_upload','9');expect(page.locator('#wireless-comparison')).to_have_text('Sesuai')
        choose('router_connector','normal');choose('switch_connector','normal');choose('signal_test','good');choose('blank_spot','false');choose('hotspot','true')
        for key in ['router_connector','switch_connector','signal_test','blank_spot','hotspot']:field(key+'_notes','Keterangan hasil pemeriksaan '+key)
        field('summary','Pemeriksaan hotel dan sampling AP selesai');choose('work_status','pending');field('pending_reason','Menunggu tindak lanjut customer')
        field('pic_exception_reason','Tanda tangan digital belum tersedia')
        page.locator('#form-dialog').evaluate('(el)=>el.scrollTop=0')
        page.screenshot(path=str(artifacts/'revised-report-backbone.png'),full_page=True)
        page.locator('#dialog-fields').get_by_role('heading',name='LOCAL AREA NETWORK',exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(artifacts/'revised-report-lan.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.locator('#form-dialog').evaluate('(el)=>el.scrollWidth<=el.clientWidth')
        page.screenshot(path=str(artifacts/'revised-report-mobile.png'),full_page=True)
        page.set_viewport_size({'width':1440,'height':1000});save()
        for name in ('Router Uji','Switch Uji'):
            card(name).locator('input[type=file]').set_input_files(photo)
            expect(card(name).locator('img')).to_have_attribute('src', __import__('re').compile('^blob:'))
        click('Check-out & kirim laporan');page.locator('#editor-form button[type=submit]').click()
        expect(page.locator('#form-error')).to_contain_text('Foto wajib')
        click('Batal')
        card('AP 2601').locator('input[type=file]').set_input_files(photo)
        expect(card('AP 2601').locator('img')).to_have_attribute('src',__import__('re').compile('^blob:'))
        page.screenshot(path=str(artifacts/'hotel-visit-photos.png'),full_page=True)
        click('Check-out & kirim laporan');save();expect(page.locator('.page-heading .badge')).to_have_text('Menunggu review')
        click('Keluar');login('web_admin');nav('Kunjungan hotel');click('Buka laporan →');click('Minta revisi laporan hotel')
        field('reason','Perjelas tindak lanjut');save()
        click('Keluar');login('web_tech');nav('Kunjungan hotel');click('Buka laporan →');click('Isi laporan utama')
        field('summary','Teknisi sudah menjelaskan tindak lanjut yang pending');save();click('Kirim ulang laporan');save()
        click('Keluar');login('web_admin');nav('Kunjungan hotel');click('Buka laporan →');click('Setujui laporan hotel')
        field('reason','Foto dan temuan ditinjau; pending diterima untuk tindak lanjut');save()
        expect(page.locator('.page-heading .badge')).to_have_text('Disetujui')
        expect(page.locator('#page-content')).to_contain_text('Laporan disetujui, pekerjaan masih pending')
        expect(page.locator('.history-event')).to_have_count(4)
        assert page.locator('article.card').count()==3
        assert page.locator('img').evaluate_all('(items)=>items.every(img=>img.complete&&img.naturalWidth>0)')
        page.screenshot(path=str(artifacts/'hotel-approved.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(artifacts/'hotel-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert page.evaluate('localStorage.length===0&&sessionStorage.length===0')
        page.reload();expect(page.locator('#login-view')).to_be_visible()
        assert not errors,errors
        browser.close()
    print('Browser flow passed: automatic LibreSpeed download/upload/ping/jitter, diagnostic isolation and cancellation; hotel photos, revision, pending approval and mobile/session checks passed.',flush=True)
