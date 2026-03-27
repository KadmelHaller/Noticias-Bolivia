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

# Keywords ultra-específicas para evitar noticias de cultura/tecnología exterior
KEYWORDS_STRICT = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "gobierno", "arce", "ministro", "economia", "dolar", "banco", "subvención", "combustible"]

if 'reporte_final' not in st.session_state: st.session_state.reporte_final = ""
if 'datos_acumulados' not in st.session_state: st.session_state.datos_acumulados = ""

# --- 2. FUNCIONES DE EXPORTACIÓN (Times New Roman 10pt) ---

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
    
    # Forzar Times New Roman
    rFonts = style.element.rPr.rFonts
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')

    # Encabezado: Espacio para el logo (Mismo formato que el archivo enviado)
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
        l_upper = linea.upper()
        # Detección de inicio de sección
        if target in l_upper and any(prefix in l_upper for prefix in ["1.", "2.", "COCHABAMBA", "SANTA CRUZ"]):
            capturando = True
            continue
        # Detección de fin de sección (cuando empieza la otra ciudad)
        other_target = "SANTA CRUZ" if target == "COCHABAMBA" else "COCHABAMBA"
        if capturando and other_target in l_upper and any(prefix in l_upper for prefix in ["1.", "2."]):
            capturando = False

        if capturando and linea.strip():
            p = doc.add_paragraph()
            # TITULARES: Negrita y Mayúsculas (detecta asteriscos de la IA)
            if "*" in linea:
                limpia = linea.replace('*', '').strip().upper()
                run = p.add_run(limpia)
                run.bold = True
            # MEDIOS: Negrita (detecta nombres de medios conocidos)
            elif any(m in l_upper for m in ["OPINIÓN", "EL DEBER", "UNITEL", "RED UNO", "LA VOZ", "VISIÓN 360", "LOS TIEMPOS", "ATB", "PAT", "INNOTICIAS", "ENFOQUE NEWS"]):
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
        # CAMBIO CLAVE: Se usa el nombre del modelo sin prefijos y se maneja la excepción
        # Si falla el 1.5-flash, intentará con gemini-pro que es más estable en v1beta
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            res = model.generate_content(tu_prompt_logic(datos_raw))
        except:
            model = genai.GenerativeModel('gemini-pro')
            res = model.generate_content(tu_prompt_logic(datos_raw))
            
        return res.text
    except Exception as e:
        return f"Error en la IA: {str(e)}"

def tu_prompt_logic(datos_raw):
    return f"""
        FECHA: {fecha_hoy}. 
        IMPORTANTE: Solo incluye noticias de BOLIVIA relacionadas con IMPUESTOS principalmente, luego ECONOMÍA y GOBIERNO. 
        Ignora cultura, tecnología, internacionales o deportes.

        ESTRUCTURA OBLIGATORIA:
        1. COCHABAMBA
        (Noticias de medios de Cbba como Opinión, Los Tiempos, Innoticias, Urgente.bo, Enfoque News y nacionales que afecten a Cochabamba)

        2. SANTA CRUZ
        (Noticias de El Deber, El Mundo, La Voz Digital, Visión 360 y nacionales que afecten a Santa Cruz)

        FORMATO POR NOTICIA:
        *TITULAR EXACTO EN MAYÚSCULAS*
        NOMBRE DEL MEDIO EN MAYÚSCULAS
        Resumen de 5 líneas con nombres y cargos exactos. Sin etiquetas.
        Enlace sin etiqueta, directo, en minúsculas.

        Regla: Usa UN asterisco (*) para el titular. El medio en la línea de abajo. 
        \n\nDATOS RECOPILADOS:\n{datos_raw}"""

# --- 4. INTERFAZ ---

st.title(f"🔍 MONITOR ESTRATÉGICO TOTAL: {fecha_hoy}")
api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    if st.button("🚀 INICIAR MONITOREO DE NOTICIAS (PASO 1 Y 2)"):
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
        pb = st.progress(0)
        for i, f in enumerate(fuentes):
            try:
                r = requests.get(f['u'], headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                soup = BeautifulSoup(r.text, 'html.parser')
                for el in soup.find_all(['h1', 'h2', 'h3']):
                    tit = el.get_text().strip()
                    if len(tit) > 30 and any(k in tit.lower() for k in KEYWORDS_STRICT):
                        datos_crudos += f"MEDIO: {f['n']} | CIUDAD: {f['r']} | NOTICIA: {tit}\n"
            except: continue
            pb.progress((i + 1) / len(fuentes))
        
        if datos_crudos:
            st.session_state.reporte_final = procesar_ia_robusta(datos_crudos)
            st.success("Monitoreo completado con filtros aplicados.")
        else:
            st.warning("No se encontraron noticias relevantes con los filtros actuales.")

    if st.session_state.reporte_final:
        st.markdown("### VISTA PREVIA DEL REPORTE")
        st.markdown(f'<div style="background:white;color:black;padding:20px;border:1px solid #ccc;font-family:serif;">{st.session_state.reporte_final.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        
        st.subheader("💾 EXPORTAR DOCUMENTOS (Times New Roman 10pt)")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("Descargar Word COCHABAMBA", generar_word_oficial(st.session_state.reporte_final, "CBBA"), f"Reporte_CBBA_{fecha_hoy.replace('/','-')}.docx")
        with c2:
            st.download_button("Descargar Word SANTA CRUZ", generar_word_oficial(st.session_state.reporte_final, "STACRUZ"), f"Reporte_STACRUZ_{fecha_hoy.replace('/','-')}.docx")
