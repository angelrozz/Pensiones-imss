"""Plataforma IMSS: generador de cinco entregables desde resultados validados.
No estima pensiones IMSS sin parámetros y validación humana.
"""
import io, json, re, zipfile, tempfile, os, hmac
from pathlib import Path
from datetime import date
import streamlit as st
import fitz
from PIL import Image, ImageDraw, ImageFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from artifact_tool import Workbook, SpreadsheetFile

NAVY='#112A46'; TEAL='#087E91'
st.set_page_config(page_title='Estrategia de Retiro IMSS',layout='wide')

# Control de acceso básico. Si falta el secreto, la aplicación se bloquea.
# Definir APP_PASSWORD solo en Render -> Environment (nunca en GitHub).
password = os.environ.get('APP_PASSWORD', '')
if len(password) < 16:
    st.error('Aplicación bloqueada: falta configurar APP_PASSWORD (mínimo 16 caracteres) en Render.')
    st.stop()

if not st.session_state.get('authorized', False):
    st.title('Acceso privado · Plataforma IMSS')
    with st.form('login'):
        entered = st.text_input('Contraseña', type='password')
        submit = st.form_submit_button('Entrar')
    if submit:
        if hmac.compare_digest(entered.encode('utf-8'), password.encode('utf-8')):
            st.session_state.authorized = True
            st.rerun()
        else:
            st.error('Contraseña incorrecta')
    st.stop()

if st.sidebar.button('Cerrar sesión'):
    st.session_state.authorized = False
    st.rerun()

st.title('Plataforma de estrategias de retiro IMSS')
st.caption('Generador de cinco entregables · Resultados estimados, sujetos a validación IMSS · No sustituye resolución oficial')


def extract_pdf(data):
    try:
        d=fitz.open(stream=data,filetype='pdf'); return '\n'.join(p.get_text() for p in d)
    except Exception: return ''

def extract_candidates(text):
    patterns={
        'semanas':r'(?:semanas\s+(?:cotizadas|reconocidas)|total\s+de\s+semanas)\s*[:\-]?\s*([\d,]+)',
        'sbc':r'(?:salario\s+base\s+de\s+cotizaci[oó]n|SBC\s+diario)\s*[:\-]?\s*\$?([\d,.]+)',
        'nss':r'\b(\d{11})\b'
    }
    return {k:(re.search(p,text,re.I).group(1) if re.search(p,text,re.I) else '') for k,p in patterns.items()}

def money(n):return 'N/D' if n is None else '${:,.0f}'.format(n)

def pension_age(age,values):return values.get(str(age))

def pdf_bytes(title,client,rows,notes):
    b=io.BytesIO(); doc=SimpleDocTemplate(b,pagesize=(612,792),rightMargin=35,leftMargin=35,topMargin=40,bottomMargin=35)
    sty=getSampleStyleSheet(); story=[Paragraph(title,sty['Title']),Paragraph(client,sty['Heading2']),Spacer(1,12)]
    data=[['Edad','Base','Modalidad 10','Meta','ROI mejora (meses)']]
    for r in rows:data.append([str(r['edad']),money(r['base']),money(r['m10']),money(r['meta']),str(r['roi']) if r['roi'] is not None else 'N/D'])
    t=Table(data,colWidths=[55,110,125,110,135],repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(NAVY)),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.4,colors.lightgrey),('BOTTOMPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),9)]))
    story.extend([t,Spacer(1,15),Paragraph('Notas y condiciones',sty['Heading2'])])
    for n in notes:story.append(Paragraph('• '+n,sty['BodyText']));story.append(Spacer(1,5))
    doc.build(story);return b.getvalue()

def infographic(client,rows):
    im=Image.new('RGB',(1200,1550),'#F3F7FA');d=ImageDraw.Draw(im)
    d.rounded_rectangle((45,45,1155,1500),radius=32,fill='white')
    d.rectangle((45,45,1155,260),fill=NAVY)
    d.text((90,105),'ESTRATEGIA DE RETIRO IMSS',fill='white',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',40))
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',27)
    bold=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',28)
    d.text((90,300),client,fill=NAVY,font=bold)
    d.text((90,365),'Edad',fill=NAVY,font=bold);d.text((275,365),'Base',fill=NAVY,font=bold);d.text((565,365),'Modalidad 10',fill=NAVY,font=bold)
    for i,r in enumerate(rows):
        y=440+i*135
        if i%2==0:d.rounded_rectangle((75,y-15,1120,y+100),radius=12,fill='#EAF2F6')
        d.text((100,y),str(r['edad']),fill=NAVY,font=bold);d.text((270,y),money(r['base']),fill=NAVY,font=font);d.text((570,y),money(r['m10']),fill=TEAL,font=font)
    d.text((90,1340),'Escenarios estimados; sujetos a requisitos y validacion.',fill=NAVY,font=font)
    b=io.BytesIO();im.save(b,format='PNG');return b.getvalue()

def excel_bytes(client,rows,notes):
    wb=Workbook.create();s=wb.worksheets.add('Proyecciones');s.get_range('A1:F1').values=[['Edad','Base mensual','M10 mensual','Meta mensual','Cuotas acumuladas','ROI mejora meses']]
    matrix=[[r['edad'],r['base'],r['m10'],r['meta'],r['cuotas'],r['roi']] for r in rows]
    s.get_range('A2:F7').values=matrix
    s.get_range('A1:F1').format.fill=NAVY;s.get_range('A1:F1').format.font.color='#FFFFFF'
    s.get_range('A:F').format.column_width=20
    s2=wb.worksheets.add('Supuestos');s2.get_range('A1:B2').values=[['Cliente',client],['Fecha',str(date.today())]]
    for i,n in enumerate(notes):s2.get_range(f'A{i+4}').values=[[n]]
    s2.get_range('A:A').format.column_width=85
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/'estudio.xlsx';SpreadsheetFile.export_xlsx(wb).save(str(path));return path.read_bytes()

def package(client,rows,notes):
    files={
      '01_Dashboard_Ejecutivo.pdf':pdf_bytes('Dashboard ejecutivo',client,rows,notes),
      '02_Infografia.png':infographic(client,rows),
      '03_Informe_Tecnico.pdf':pdf_bytes('Informe tecnico de pension',client,rows,notes),
      '04_Estudio_Calculos.xlsx':excel_bytes(client,rows,notes),
      '05_Recomendacion_Estrategica.pdf':pdf_bytes('Recomendacion estrategica',client,rows,notes),
      'datos_y_supuestos.json':json.dumps({'cliente':client,'escenarios':rows,'notas':notes},ensure_ascii=False,indent=2).encode()
    }
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for name,content in files.items():z.writestr(name,content)
    return b.getvalue()

uploads=st.file_uploader('Sube constancia de semanas y/o estado de cuenta Afore (PDF)',type=['pdf'],accept_multiple_files=True)
if uploads:
    for f in uploads:
        candidates=extract_candidates(extract_pdf(f.getvalue()))
        st.write(f.name,'· Datos candidatos (confirmar contra documento):',candidates)
client=st.text_input('Nombre del prospecto','Prospecto nuevo')
regimen=st.selectbox('Régimen',['Ley 73','Ley 97','Por determinar'])
semanas=st.number_input('Semanas reconocidas',min_value=0,value=0)
notes=[f'Régimen declarado: {regimen}. Semanas reconocidas declaradas: {semanas}.',
       'Las cifras son escenarios introducidos y validados por el asesor; no son cálculo automático de pensión IMSS.',
       'Modalidad 10 depende de elegibilidad, cotización efectiva, cuotas y reglas aplicables.',
       'ROI mejora = cuotas acumuladas / (pensión M10 - pensión base), solo cuando ambas rutas son comparables.',
       'Validar conservación de derechos, requisitos, saldos y resolución del IMSS.']
if regimen=='Ley 73' and semanas<500:st.warning('Menos de 500 semanas reconocidas: la pensión Ley 73 no está acreditada con estos datos.')
st.subheader('Escenarios validados para edades 60–65')
st.info('Ingresa los valores auditados de tu modelo existente. Los campos vacíos permanecen N/D; no se inventan pensiones.')
rows=[]
for age in range(60,66):
    with st.expander(f'Edad {age}',expanded=age==60):
        a,b,c,d=st.columns(4)
        base=a.number_input('Pensión base',min_value=0.,value=0.,key=f'b{age}')
        m10=b.number_input('Pensión M10',min_value=0.,value=0.,key=f'm{age}')
        cuotas=c.number_input('Cuotas acumuladas M10',min_value=0.,value=0.,key=f'c{age}')
        meta=d.selectbox('Meta',options=[20000,35000,50000],key=f't{age}')
        base=base or None;m10=m10 or None;cuotas=cuotas or None
        roi=round(cuotas/(m10-base),1) if all(x is not None for x in [base,m10,cuotas]) and m10>base else None
        rows.append(dict(edad=age,base=base,m10=m10,cuotas=cuotas,meta=meta,roi=roi))
notes.append(st.text_area('Observaciones del asesor','No se garantizan resultados.'))
if st.button('Generar los cinco entregables',type='primary'):
    data=package(client,rows,notes)
    st.download_button('Descargar expediente ZIP',data,file_name='Expediente_IMSS_'+re.sub(r'\W+','_',client)+'.zip',mime='application/zip')

# Mobile-first usability: the app can be opened in Safari once hosted over HTTPS.
st.markdown('''<style>
@media(max-width:700px){
 .block-container{padding:1rem .7rem 5rem!important;max-width:100%!important}
 h1{font-size:1.65rem!important;line-height:1.15!important}
 [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important;gap:.5rem!important}
 [data-testid="column"]{min-width:100%!important;flex:1 1 100%!important}
 .stButton button,.stDownloadButton button{width:100%;min-height:48px}
 input,textarea{font-size:16px!important}
}
</style>''',unsafe_allow_html=True)
with st.expander('Guardar / recuperar captura (iPhone y laptop)'):
    st.caption('Descarga un JSON para conservar la captura sin almacenar datos personales en un servidor.')
    snapshot={'cliente':client,'regimen':regimen,'semanas':semanas,'escenarios':rows,'notas':notes}
    st.download_button('Guardar captura JSON',json.dumps(snapshot,ensure_ascii=False,indent=2).encode('utf-8'),file_name='captura_'+re.sub(r'\W+','_',client)+'.json',mime='application/json')
    prior=st.file_uploader('Consultar una captura anterior (JSON)',type=['json'],key='restore')
    if prior:
        try:
            saved=json.loads(prior.getvalue()); st.json(saved)
            st.info('Para aplicar esta captura a un nuevo expediente, utiliza sus cifras auditadas en los campos superiores.')
        except (ValueError,UnicodeDecodeError): st.error('JSON inválido.')
