import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import os
import time
from io import BytesIO
from urllib.parse import urlparse
from docx import Document
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Estratégico Bolivia", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

KEYWORDS_STRICT = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "gobierno", "arce", "ministro", "economia", "dolar", "banco", "subvención", "combustible"]

if 'reporte_final' not in st.session_state: st.session_state.reporte_final = ""

# --- 2. FUNCIONES DE EXPORTACIÓN ---

def obtener_info_envio():
    ahora = datetime.now(zona_horaria)
    hm = ahora.hour * 100 + ahora.minute
    if 830 <= hm <= 930: return "1er Envío"
    elif 1330 <= hm <= 1430: return "2do Envío"
    elif 1530 <= hm <= 1630: return "3er Envío"
    return "Envío Extraordinario"

def generar_word_oficial(texto, ciudad_tag):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(10)
    
    # Forzar Times New Roman en el XML
    rFonts = style.element.rPr.rFonts
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')

    # Encabezado: Espacio para el logo
    section = doc.sections[0]
    section.header.paragraphs[0].add_run("\n\n")

    doc.add_paragraph("N°")
    doc.add_paragraph(fecha_hoy)
    doc.add_paragraph(obtener_info_envio())
    doc.add_paragraph("")

    target = "COCHABAMBA" if ciudad_tag == "CBBA" else "SANTA CRUZ"
    lineas = texto.split('\n')
    capturando = False
    
    for linea in lineas:
        l_upper = linea.upper().strip()
        
        # Lógica de detección de secciones mejorada
        if target in l_upper and any(p in l_upper for p in ["1.", "2.", "SECCIÓN"]):
            capturando = True
            continue
        
        # Si capturamos y llegamos a la siguiente sección numérica, paramos
        if capturando and any(p in l_upper for p in ["1.", "2."]) and target not in l_upper:
            capturando = False

        if capturando and linea.strip():
            p = doc.add_paragraph()
            # TITULARES
            if "*" in linea:
                limpia = linea.replace('*', '').strip().upper()
                run = p.add_run(limpia)
                run.bold = True
            # MEDIOS
            elif any(m in l_upper for m in ["OPINIÓN", "EL DEBER", "UNITEL", "RED UNO", "LA VOZ", "VISIÓN 360", "LOS TIEMPOS", "ATB", "PAT"]):
                run = p.add_run(l_upper)
                run.bold = True
            else:
                p.add_run(linea)
            p.paragraph_format.space_after = Pt(4)

    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. PROCESAMIENTO E IA ---

def procesar_ia_robusta(datos_raw):
    try:
        # Cambiado a 'gemini-1.5-flash' para mayor compatibilidad
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        FECHA: {fecha_hoy}. 
        IMPORTANTE: Solo incluye noticias de BOLIVIA relacionadas con IMPUESTOS, ECONOMÍA y GOBIERNO. 
        Ignora cultura, tecnología, internacionales o deportes.

        ESTRUCTURA OBLIGATORIA:
        1. COCHABAMBA
        (Incluye noticias de Opinión, Los Tiempos, Enfoque News y nacionales de Cbba)

        2. SANTA CRUZ
        (Incluye noticias de El Deber, La Voz Digital, Visión 360 y nacionales de SCZ)

        FORMATO POR NOTICIA:
        *TITULAR EXACTO EN MAYÚSCULAS*
        NOMBRE DEL MEDIO EN MAYÚSCULAS
        Resumen de 5 líneas con nombres y cargos exactos.
        Enlace directo en minúsculas.

        Regla: Usa UN asterisco (*) para el titular. El medio en la línea de abajo. No uses negritas de markdown (**).
        """
        res = model.generate_content(prompt + "\n\nDATOS RECOPILADOS:\n" + datos_raw)
        return res.text
    except Exception as e:
        return f"Error en la IA: {str(e)}"

# --- 4. INTERFAZ ---

st.title(f"🔍 MONITOR ESTRATÉGICO TOTAL: {fecha_hoy}")
api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    if st.button("🚀 INICIAR MONITOREO DE NOTICIAS"):
        fuentes = [
            {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba"},
            {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "r": "Cochabamba"},
            {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "r": "Santa Cruz"},
            {"n": "LA VOZ DIGITAL", "u": "https://lavoz.digital/", "r": "Santa Cruz"},
            {"n": "VISIÓN 360", "u": "https://www.vision360.bo/", "r": "Nacional"},
            {"n": "UNITEL", "u": "https://unitel.bo/", "r": "Nacional"},
            {"n": "RED UNO", "u": "https://www.reduno.com.bo/", "r": "Nacional"}
        ]
        
        datos_crudos = ""
        progress_text = st.empty()
        pb = st.progress(0)
        
        for i, f in enumerate(fuentes):
            progress_text.text(f"Escaneando: {f['n']}...")
            try:
                r = requests.get(f['u'], headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                soup = BeautifulSoup(r.text, 'html.parser')
                for el in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                    tit = el.get_text().strip()
                    if len(tit) > 30 and any(k in tit.lower() for k in KEYWORDS_STRICT):
                        datos_crudos += f"MEDIO: {f['n']} | CIUDAD: {f['r']} | NOTICIA: {tit}\n"
            except: continue
            pb.progress((i + 1) / len(fuentes))
        
        if datos_crudos:
            st.session_state.reporte_final = procesar_ia_robusta(datos_crudos)
            st.success("Monitoreo completado.")
        else:
            st.warning("No se hallaron noticias con los filtros actuales.")

    if st.session_state.reporte_final:
        st.markdown("### VISTA PREVIA")
        st.markdown(f'<div style="background:white;color:black;padding:20px;border:1px solid #ccc;font-family:serif;">{st.session_state.reporte_final.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        
        st.subheader("💾 EXPORTAR")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("Descargar Word CBBA", generar_word_oficial(st.session_state.reporte_final, "CBBA"), f"Reporte_CBBA_{fecha_hoy.replace('/','-')}.docx")
        with c2:
            st.download_button("Descargar Word STACRUZ", generar_word_oficial(st.session_state.reporte_final, "STACRUZ"), f"Reporte_STACRUZ_{fecha_hoy.replace('/','-')}.docx")
