"""Run only against the disposable staging server created by run_web_staging.py."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def run(base_url, password, artifacts):
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(viewport={'width':1440,'height':1000},locale='id-ID',
                                    permissions=['geolocation'],geolocation={'latitude':-6.2,'longitude':106.8})
        page=context.new_page()
        page.on('pageerror',lambda error: errors.append(str(error)))
        def login(username):
            page.goto(base_url)
            page.locator('[name=username]').fill(username)
            page.locator('[name=password]').fill(password)
            page.get_by_role('button',name='Masuk ke workspace').click()
            expect(page.locator('#workspace')).to_be_visible()
        def nav(name):
            page.locator('#navigation').get_by_role('button',name=name,exact=True).click()
        def save():
            page.locator('#editor-form button[type=submit]').click()
            expect(page.locator('#form-dialog')).not_to_be_visible()
        def add(name):
            page.get_by_role('button',name=name,exact=True).click()
        def field(name,value):
            page.locator('#dialog-fields [name='+name+']').fill(value)
        login('web_admin')
        page.screenshot(path=str(artifacts/'dashboard-empty.png'),full_page=True)
        nav('Hotel');add('＋ Tambah hotel');field('name','Hotel Uji Browser');field('address','Alamat khusus staging');save()
        expect(page.get_by_role('cell',name='Hotel Uji Browser',exact=True)).to_be_visible()
        nav('Perangkat');add('＋ Tambah perangkat')
        page.locator('[name=hotel_id]').select_option(label='Hotel Uji Browser')
        field('name','AP Lobby');page.locator('[name=device_type]').select_option('ap');field('serial_number','TEST-ONLY')
        field('brand','Brand Uji');field('model','AP Model Uji');field('location','Lobby lantai 1')
        field('ip_address','192.168.20.2');field('mac_address','AA-BB-CC-DD-EE-FF');field('notes','Catatan inventaris staging');save()
        expect(page.get_by_role('cell',name='Lobby lantai 1 192.168.20.2')).to_be_visible()
        add('Ubah');expect(page.locator('[name=brand]')).to_have_value('Brand Uji')
        expect(page.locator('[name=mac_address]')).to_have_value('aa:bb:cc:dd:ee:ff')
        page.get_by_role('button',name='Batal',exact=True).click()
        nav('Tim');add('＋ Tambah tim');field('username','web_tech');field('name','Teknisi Uji');field('password',password);save()
        nav('Template checklist');add('＋ Tambah template checklist');field('name','AP Preventive v1')
        page.locator('[name=device_type]').select_option('ap');field('items','Periksa kabel jaringan\nPeriksa daya perangkat');save()
        nav('Jadwal');add('＋ Tambah jadwal')
        page.locator('[name=device_id]').select_option(label='Hotel Uji Browser / AP Lobby')
        page.locator('[name=technician_id]').select_option(label='Teknisi Uji');field('month','2026-11');save()
        add('Buat kunjungan →');page.locator('[name=template_id]').select_option(label='AP Preventive v1');save()
        nav('Ringkasan');page.screenshot(path=str(artifacts/'dashboard.png'),full_page=True)
        page.get_by_role('button',name='Keluar',exact=True).click()
        login('web_tech')
        expect(page.locator('#navigation')).not_to_contain_text('Tim')
        nav('Kunjungan');add('Buka kunjungan →');add('Mulai kunjungan / check-in');save()
        expect(page.locator('[data-save-checklist]')).to_be_visible()
        selects=page.locator('[data-item]');selects.nth(0).select_option('fail');selects.nth(1).select_option('pass')
        page.locator('[data-notes]').nth(0).fill('Kabel perlu diganti')
        add('Simpan jawaban');expect(page.locator('#notice')).to_contain_text('tersimpan')
        add('Check-out & kirim laporan');field('pic_exception_reason','PIC tidak tersedia pada kunjungan uji');save()
        expect(page.locator('.page-heading .badge')).to_have_text('Menunggu review')
        page.get_by_role('button',name='Keluar',exact=True).click()
        login('web_admin');nav('Kunjungan');add('Buka kunjungan →');add('Minta revisi');field('reason','Ganti kabel dan catat tindakan');save()
        expect(page.locator('.page-heading .badge')).to_have_text('Perlu revisi')
        page.get_by_role('button',name='Keluar',exact=True).click()
        login('web_tech');nav('Kunjungan');add('Buka kunjungan →')
        page.locator('[data-item]').nth(0).select_option('pass');page.locator('[data-notes]').nth(0).fill('Kabel sudah diganti dan diuji')
        add('Simpan jawaban');expect(page.locator('#notice')).to_contain_text('tersimpan')
        add('Kirim ulang untuk review');save()
        page.get_by_role('button',name='Keluar',exact=True).click()
        login('web_admin');nav('Kunjungan');add('Buka kunjungan →');add('Setujui laporan')
        field('reason','Perbaikan sudah ditinjau; pengecualian PIC diterima');save()
        expect(page.locator('.page-heading .badge')).to_have_text('Disetujui')
        expect(page.locator('.history-event')).to_have_count(4)
        page.screenshot(path=str(artifacts/'approved-visit.png'),full_page=True)
        nav('Jadwal');expect(page.get_by_role('cell',name='Selesai',exact=True)).to_be_visible()
        assert page.evaluate('localStorage.length')==0
        assert page.evaluate('sessionStorage.length')==0
        page.set_viewport_size({'width':390,'height':844});nav('Kunjungan')
        page.screenshot(path=str(artifacts/'mobile-visits.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.reload();expect(page.locator('#login-view')).to_be_visible()
        assert not errors, errors
        browser.close()
    print('Browser flow passed: master data → assignment → check-in → checklist → revision → resubmit → approval; mobile and memory-only session verified.',flush=True)
