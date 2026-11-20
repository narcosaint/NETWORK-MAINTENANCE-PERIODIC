"""Nusanet maintenance report from immutable PIC-reviewed inputs."""
from io import BytesIO
from pathlib import Path
from reportlab.lib.utils import ImageReader
from PIL import Image as RasterImage
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable, KeepTogether
from app.hotel_api import storage

LABELS={'fo':'Backbone Fiber Optic','wireless':'Wireless Backbone','summary':'Ringkasan',
 'download_mbps':'Download (Mbps)','upload_mbps':'Upload (Mbps)','agreement_download_mbps':'Service Agreement Download (Mbps)',
 'agreement_upload_mbps':'Service Agreement Upload (Mbps)','link_test_download_mbps':'Link Test Radio Download (Mbps)',
 'link_test_upload_mbps':'Link Test Radio Upload (Mbps)','signal_dbm':'Signal Strength (dBm)','tx_mbps':'TX Rate (Mbps)',
 'rx_mbps':'RX Rate (Mbps)','ccq_percent':'CCQ (%)','conformity':'Kesesuaian','notes':'Keterangan',
 'minimum_percent':'Minimum (%)','router_connector':'Koneksi LAN Router','switch_connector':'Koneksi LAN Switch',
 'signal_test':'Signal Test','blank_spot':'Blank Spot Area','hotspot':'Hotspot','work_status':'Hasil Pekerjaan',
 'pending_reason':'Alasan Pending','customer_company':'Nama Pelanggan','pic_name':'PIC','pic_contact':'Kontak PIC',
 'backbone_mode':'Jenis Koneksi Backbone','findings':'Temuan','action':'Tindakan','recommendation':'Rekomendasi',
 'condition':'Kondisi','customer_feedback':'Feedback Pelanggan','solution':'Solusi','lan_notes':'Keterangan LAN Lama',
 'link_test_radio':'Link Test Radio Lama','speedtest_mbps':'Speedtest Lama (Mbps)','agreement_mbps':'Service Agreement Lama (Mbps)',
 'source':'Sumber','conformity_reason':'Dasar Kesesuaian','pic_exception_reason':'Catatan PIC Lama',
 'form_version':'Versi Form','ssid':'SSID','bssid':'BSSID','frequency_mhz':'Frekuensi (MHz)','rssi_dbm':'RSSI (dBm)',
 'link_speed_mbps':'Link Speed (Mbps)','ip_address':'IP Address','gateway':'Gateway','observed_at':'Waktu Pembacaan',
 'transport':'Transport','ping_ms':'Ping (ms)','jitter_ms':'Jitter (ms)'}
VALUES={'good':'Baik','attention':'Perlu Perhatian','problem':'Bermasalah','untested':'Belum Diperiksa',
 'normal':'Normal','abnormal':'Tidak Normal','not_applicable':'Tidak Berlaku','poor':'Kurang Baik',
 'completed':'Selesai','pending':'Pending','failed':'Gagal Diuji','aborted':'Dibatalkan','conforming':'Sesuai',
 'not_conforming':'Tidak Sesuai','fo_only':'Fiber Optic','wireless_only':'Wireless','both':'FO + Wireless',
 'failover':'FO + Wireless / Failover','bonding':'FO + Wireless / Bonding','manual':'Input Teknisi','android_native':'Android Native','profile_missing':'Profil layanan belum ditetapkan','measurement_missing':'Pengukuran belum tersedia','calculated':'Dihitung dari service agreement'}


class Signature(Flowable):
    def __init__(self,strokes):
        Flowable.__init__(self);self.width=85*mm;self.height=30*mm;self.strokes=strokes
    def draw(self):
        self.canv.setStrokeColor(colors.HexColor('#123d35'));self.canv.setLineWidth(1.4)
        for stroke in self.strokes:
            if not stroke:continue
            path=self.canv.beginPath();path.moveTo(stroke[0][0]*self.width,(1-stroke[0][1])*self.height)
            for x,y in stroke[1:]:path.lineTo(x*self.width,(1-y)*self.height)
            self.canv.drawPath(path)


def make_pdf(snapshot,status,preview=False):
    output=BytesIO(); styles=getSampleStyleSheet();styles['Normal'].fontSize=9;styles['Normal'].leading=13
    styles['Heading1'].textColor=colors.HexColor('#0c7559');styles['Heading2'].textColor=colors.HexColor('#0c7559')
    story=[];data=snapshot['document'];report=data['report']
    def p(value,style='Normal'):
        if value is None:value='Belum tersedia'
        elif isinstance(value,bool):value='Ya' if value else 'Tidak'
        else:value=VALUES.get(str(value),str(value))
        return Paragraph(escape(str(value)).replace('\n','<br/>'),styles[style])
    def title(value):story.extend([p(value,'Heading2'),Spacer(1,2*mm)])
    def rows(values):
        if not values:
            story.append(p("Belum tersedia"));return
        table=Table([[p(label),p(value)] for label,value in values],colWidths=[60*mm,112*mm],hAlign='LEFT')
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#edf6f2')),
            ('BOX',(0,0),(-1,-1),.3,colors.lightgrey),('INNERGRID',(0,0),(-1,-1),.2,colors.lightgrey),
            ('LEFTPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([table,Spacer(1,3*mm)])
    def items(mapping):
        return [(LABELS.get(k,k.replace('_',' ').title()),v) for k,v in mapping.items() if v is not None and not isinstance(v,(dict,list))]
    brand=Path(__file__).resolve().parent/'web'/'brand'
    logo=Image(str(brand/'nusa-maintenance-logo.png'),width=95*mm,height=30*mm)
    icon=Image(str(brand/'nusa-maintenance-icon.png'),width=17*mm,height=17*mm)
    heading=Table([[logo,icon]],colWidths=[150*mm,22*mm]);heading.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(1,0),(1,0),'RIGHT')]))
    story.extend([heading,Spacer(1,4*mm)])
    story.append(p('FORM MAINTENANCE PERIODIK','Title'))
    story.append(p('NUSA MAINTENANCE · Preventive Maintenance Jaringan Hotel'))
    if preview:story.append(p('DRAF UNTUK REVIEW PIC - BELUM DITANDATANGANI','Heading1'))
    story.append(p('Disetujui supervisor' if status=='approved' else 'Menunggu review supervisor' if status=='submitted' else 'Belum diajukan / perlu revisi'))
    title('A. Informasi Pelanggan')
    rows([('Nama Hotel',data['hotel']['name']),('Alamat',data['hotel']['address']),('Nama Pelanggan',report.get('customer_company') or data['hotel'].get('customer_name')),
          ('Tanggal Maintenance',data['planned_date']),('Teknisi',data['technician']['name']),('ID Kunjungan',data['visit_id']),
          ('PIC',snapshot['signature']['name']),('Jabatan PIC',snapshot['signature']['position']),('Kontak PIC',report.get('pic_contact'))])
    for label,key in [('B. Backbone Fiber Optic','fo'),('C. Wireless Backbone','wireless')]:
        branch_start=len(story)
        title(label)
        if report.get(key):
            branch=report[key]
            keys=['agreement_download_mbps','agreement_upload_mbps','download_mbps','upload_mbps','conformity','conformity_reason']
            if key=='wireless':keys=['signal_dbm','link_test_download_mbps','link_test_upload_mbps','download_mbps','upload_mbps','agreement_download_mbps','agreement_upload_mbps','conformity']
            rows([((('Bandwidth Test Download (Mbps)' if field=='download_mbps' else 'Bandwidth Test Upload (Mbps)') if key=='wireless' and field in ('download_mbps','upload_mbps') else LABELS.get(field,field)),branch.get(field)) for field in keys]+[(LABELS.get(field,field),branch[field]) for field in ('agreement_mbps','speedtest_mbps','link_test_radio') if branch.get(field) is not None])
        else:story.append(p('Tidak termasuk jenis backbone yang diperiksa.'))
        story[branch_start:]=[KeepTogether(story[branch_start:])]
    title('D. Local Area Network')
    rows([(LABELS.get(key,LABELS.get(key.removesuffix("_notes"),key)+" - Keterangan"),report.get(key)) for key in ('router_connector','switch_connector','signal_test','blank_spot','hotspot') for key in (key,key+'_notes')])
    title('E. Hasil Pekerjaan')
    rows([('Ringkasan Pemeriksaan',report.get('summary')),('Status Pekerjaan',report.get('work_status'))]+([('Alasan Pending',report.get('pending_reason'))] if report.get('work_status')=='pending' else []))
    title('F. Network Test per Lantai / Area')
    for floor in data['floors']:
        story.append(p(f"{floor['name']} · {len(floor['points'])} area",'Heading3'))
        for point in floor['points']:
            story.append(p(point['name'],'Heading3'))
            observation=point.get('observation') or {}; connection=observation.get('wifi_connection') or {}
            note=observation.get('notes') or {}
            combined='\n'.join(str(value) for value in (note.get('notes'),('Temuan: '+note['findings']) if note.get('findings') else None,('Tindakan: '+note['action']) if note.get('action') else None) if value)
            rows([('Kondisi',note.get('condition')),('Temuan dan Tindakan',combined or '-')])
            if connection:
                frequency=connection.get('frequency_mhz');channel=None
                if frequency==2484:channel=14
                elif frequency and 2412<=frequency<=2472:channel=(frequency-2407)//5
                elif frequency and 5000<=frequency<5925:channel=(frequency-5000)//5
                rows(items(connection)+[('Band','2.4 GHz' if frequency and frequency<2500 else '5 GHz'),('Channel',channel)])
            else:story.append(p('Data Wi-Fi tidak tersedia; lihat alasan gagal uji.'))
            for attempt in point.get('speedtests',[]):
                run=attempt.get('run') or {};ctx=run.get('context') or {}
                rows([('Status Speedtest',attempt['status']),('Waktu Uji',attempt.get('created_at')),('Test Server',ctx.get('endpoint_origin')),
                    ('Engine',ctx.get('engine')),('Alasan Gagal',attempt.get('error'))]+items(run.get('metrics') or {}))
    title('G. Dokumentasi')
    names={point['id']:floor['name']+' / '+point['name'] for floor in data['floors'] for point in floor['points']}
    for photo in data['photos']:
        with RasterImage.open(storage()/photo['object_key']) as original:
            original.thumbnail((1600,1600));compressed=BytesIO();original.save(compressed,'JPEG',quality=82)
        compressed.seek(0);image=Image(compressed)
        ratio=min((155*mm)/image.imageWidth,(85*mm)/image.imageHeight)
        image.drawWidth=image.imageWidth*ratio;image.drawHeight=image.imageHeight*ratio
        story.append(KeepTogether([p(names.get(photo['session_id'],'Infrastruktur')+' · '+photo['category'],'Heading3'),image,
            p(photo['caption']),p(photo['captured_at']),Spacer(1,3*mm)]))
    signature_start=len(story)
    title('H. Persetujuan PIC')
    story.extend([p('Belum disetujui PIC.' if preview else 'PIC telah meninjau laporan beserta hasil pengukuran dan menyetujui isi laporan ini.'),Signature(snapshot['signature']['strokes'])])
    rows([('Nama PIC',snapshot['signature']['name']),('Jabatan PIC',snapshot['signature']['position']),('Waktu Tanda Tangan (UTC)',snapshot['signed_at']),
        ('SHA-256 Isi Laporan',snapshot['document_digest'])])
    story.append(p('Hasil radio/throughput dibaca oleh aplikasi pada HP teknisi. Tanda tangan adalah goresan persetujuan PIC, bukan sertifikat elektronik.'))
    story[signature_start:]=[KeepTogether(story[signature_start:])]
    def footer(canvas,doc):
        canvas.saveState();canvas.setFillAlpha(0.035);canvas.drawImage(ImageReader(str(brand/'nusa-maintenance-icon.png')),45*mm,85*mm,width=120*mm,height=120*mm,mask='auto');canvas.restoreState()
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.grey)
        canvas.drawString(18*mm,12*mm,'DRAF BELUM DITANDATANGANI' if preview else 'NUSANET · NUSA MAINTENANCE');canvas.drawRightString(192*mm,12*mm,f'Halaman {doc.page}')
    SimpleDocTemplate(output,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=16*mm,bottomMargin=20*mm,
        title='Nusanet Maintenance '+data['hotel']['name'],author='NUSA MAINTENANCE').build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
