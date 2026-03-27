import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import time
from io import BytesIO
from urllib.parse import urlparse
from docx import Document
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTADOS ---
st.set_page_config(page_title="Monitor Estratégico Bolivia", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "gobierno", "arce", "ministro", "estado", "economia", "dolar", "banco", "crisis"]

if 'reporte_final' not in st.session_state: st.session_state.reporte_final = ""
if 'datos_medios' not in st.session_state: st.session_state.datos_medios = ""
if 'datos_rrss' not in st.session_state: st.session_state.datos_rrss = ""

# --- 2. FUNCIONES DE APOYO ---

def obtener_info_envio():
    ahora = datetime.now(zona_horaria)
    hm = ahora.hour * 100 + ahora.minute
    if 830 <= hm <= 930: return "1er Envío"
    elif 1330 <= hm <= 1430: return "2do Envío"
    elif 1530 <= hm <= 1630: return "3er Envío"
    return "Envío Extraordinario"

def scraping_funcional(fuentes):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
    acumulado = ""
    progress_bar = st.progress(0)
    for i, f in enumerate(fuentes):
        try:
            r = requests.get(f['u'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            elementos = soup.find_all(['a', 'h1', 'h2', 'h3', 'h4'])
            for el in elementos:
                tit = el.get_text().strip()
                url = el.get('href', '')
                if len(tit) > 25 and any(k in (tit + url).lower() for k in KEYWORDS):
                    if not url.startswith('http'):
                        base = urlparse(f['u']).scheme + "://" + urlparse(f['u']).netloc
                        url = base + "/" + url.lstrip('/')
                    acumulado += f"FUENTE: {f['n']} | CIUDAD: {f['r']} | TITULAR: {tit} | URL: {url}\n\n"
        except: continue
        progress_bar.progress((i + 1) / len(fuentes))
    return acumulado

def procesar_ia(datos_prensa, datos_rrss):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    FECHA: {fecha_hoy}.
    TAREA: Reporte unificado de prensa y redes sociales.
    INSTRUCCIONES CRÍTICAS:
    1. TITULARES: Usa el texto EXACTO de la fuente, siempre en MAYÚSCULAS.
    2. PERSONAS: Identifica nombres y cargos. Escríbelos EXACTAMENTE como aparecen.
    3. RRSS: Integra las publicaciones dentro de la ciudad (Cochabamba o Santa Cruz) que corresponda.
    4. FORMATO: *TITULAR EXACTO* (un solo asterisco antes y después). En la línea de abajo el MEDIO. Luego resumen de 5 líneas y link.
    5. ESTRUCTURA: Solo dos secciones: 1. COCHABAMBA y 2. SANTA CRUZ.
    """
    contenido = f"PRENSA Y DIGITAL:\n{datos_prensa}\n\nREDES SOCIALES:\n{datos_rrss}"
    res = model.generate_content(prompt + "\n\nDATOS RECOPILADOS:\n" + contenido)
    return res.text

def generar_word_oficial(texto, ciudad_tag):
    doc = Document()
    
    # Configuración Times New Roman 10pt
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(10)
    
    # Forzar la fuente en el XML de Word
    rFonts = style.element.rPr.rFonts
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')

    # Espacio para el Logo (Encabezado vacío para pegado manual)
    section = doc.sections[0]
    section.header.paragraphs[0].add_run("\n\n") # Espacio para el logo

    # Cuerpo del mensaje (Formato del archivo enviado)
    doc.add_paragraph("N°")
    doc.add_paragraph(fecha_hoy)
    doc.add_paragraph(obtener_info_envio())
    doc.add_paragraph("") # Espacio tras el encabezado

    target = "COCHABAMBA" if ciudad_tag == "CBBA" else "SANTA CRUZ"
    capturando = False
    
    for linea in texto.split('\n'):
        if target in linea.upper() and ("1." in linea or "2." in linea):
            capturando = True
            continue
        if capturando and any(x in linea.upper() for x in ["1. COCHABAMBA", "2. SANTA CRUZ"]) and target not in linea.upper():
            capturando = False
        
        if capturando and linea.strip():
            p = doc.add_paragraph()
            # Formato de Titular: Negrita y Mayúsculas (Limpiando asteriscos)
            if linea.startswith('*') and linea.endswith('*'):
                run = p.add_run(linea.replace('*', '').upper())
                run.bold = True
            # Formato de Medio: Negrita (Detectando por palabras clave de fuentes)
            elif any(m in linea.upper() for m in ["OPINIÓN", "EL DEBER", "UNITEL", "RED UNO", "LA VOZ", "VISIÓN 360", "LOS TIEMPOS", "ATB", "PAT"]):
                run = p.add_run(linea.upper())
                run.bold = True
            else:
                p.add_run(linea)
            p.paragraph_format.space_after = Pt(4)
    
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. INTERFAZ ---

st.title(f"🔍 MONITOR ESTRATÉGICO TOTAL: {fecha_hoy}")
api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    col_botones = st.columns(2)
    
    with col_botones[0]:
        if st.button("🚀 PASO 1: REPORTE DE MEDIOS"):
            medios = [
                {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba"},
                {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "r": "Cochabamba"},
                {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "r": "Santa Cruz"},
                {"n": "LA VOZ DIGITAL", "u": "https://lavoz.digital/", "r": "Santa Cruz"},
                {"n": "VISIÓN 360", "u": "https://www.vision360.bo/", "r": "Nacional"},
                {"n": "UNITEL", "u": "https://unitel.bo/", "r": "Nacional"},
                {"n": "RED UNO", "u": "https://www.reduno.com.bo/", "r": "Nacional"}
            ]
            st.session_state.datos_medios = scraping_funcional(medios)
            st.session_state.reporte_final = procesar_ia(st.session_state.datos_medios, "")
            st.success("Reporte de medios generado.")

    with col_botones[1]:
        if st.session_state.datos_medios and st.button("📱 PASO 2: AGREGAR RRSS"):
            rrss = [
                {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=impuestos+Cochabamba+site:facebook.com+OR+site:x.com&tbs=qdr:d", "r": "Cochabamba"},
                {"n": "RRSS SCZ", "u": "https://www.google.com/search?q=impuestos+Santa+Cruz+site:facebook.com+OR+site:x.com&tbs=qdr:d", "r": "Santa Cruz"}
            ]
            st.session_state.datos_rrss = scraping_funcional(rrss)
            st.session_state.reporte_final = procesar_ia(st.session_state.datos_medios, st.session_state.datos_rrss)
            st.success("Redes Sociales integradas.")

    if st.session_state.reporte_final:
        st.markdown("### VISTA PREVIA")
        st.markdown(f'<div style="background:white;color:black;padding:20px;border:1px solid #ccc;font-family:serif;">{st.session_state.reporte_final.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("💾 PASO 3: EXPORTAR DOCUMENTOS")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📄 Descargar Word CBBA", generar_word_oficial(st.session_state.reporte_final, "CBBA"), f"Reporte_CBBA_{fecha_hoy.replace('/','-')}.docx")
        with c2:
            st.download_button("📄 Descargar Word STACRUZ", generar_word_oficial(st.session_state.reporte_final, "STACRUZ"), f"Reporte_SCZ_{fecha_hoy.replace('/','-')}.docx")
else:
    st.info("Configura tu API Key en la barra lateral para comenzar.")
