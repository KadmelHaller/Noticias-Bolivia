import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import os
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Monitor Bolivia", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# Inicializar estados de sesión para evitar recargas de pantalla en blanco
if 'reporte_final' not in st.session_state: st.session_state.reporte_final = ""
if 'datos_medios' not in st.session_state: st.session_state.datos_medios = ""
if 'datos_rrss' not in st.session_state: st.session_state.datos_rrss = ""

# --- 2. FUNCIONES DE EXPORTACIÓN (Times New Roman 10pt) ---
def generar_word_oficial(texto, ciudad_tag):
    doc = Document()
    
    # Estilo base
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(10)
    
    # Forzar Times New Roman en XML
    rFonts = style.element.rPr.rFonts
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')

    # Encabezado con Logo
    section = doc.sections[0]
    header = section.header
    header_para = header.paragraphs[0]
    if os.path.exists("logo.png"):
        run_logo = header_para.add_run()
        run_logo.add_picture("logo.png", width=Inches(1.5))

    # Determinar Envío por hora
    ahora = datetime.now(zona_horaria)
    hm = ahora.hour * 100 + ahora.minute
    if 830 <= hm <= 930: envio = "1er Envío"
    elif 1330 <= hm <= 1430: envio = "2do Envío"
    elif 1530 <= hm <= 1630: envio = "3er Envío"
    else: envio = "Envío Extraordinario"

    # Datos iniciales
    doc.add_paragraph("N°")
    doc.add_paragraph(fecha_hoy)
    doc.add_paragraph(envio)
    doc.add_paragraph("")

    # Filtrado Lógico
    target = "COCHABAMBA" if ciudad_tag == "CBBA" else "SANTA CRUZ"
    lineas = texto.split('\n')
    capturando = False
    
    for linea in lineas:
        if target in linea.upper() and any(x in linea for x in ["1.", "2."]):
            capturando = True
            continue
        if capturando and any(x in linea.upper() for x in ["1. COCHABAMBA", "2. SANTA CRUZ"]) and target not in linea.upper():
            capturando = False
            
        if capturando and linea.strip():
            p = doc.add_paragraph()
            # Formato Titular (Negrita y Mayúsculas)
            if linea.startswith('*') and linea.endswith('*'):
                run = p.add_run(linea.replace('*', '').upper())
                run.bold = True
            # Formato Medio (Negrita)
            elif len(linea) < 50 and any(m in linea.upper() for m in ["OPINIÓN", "EL DEBER", "UNITEL", "RED UNO"]):
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
api_key = st.sidebar.text_input("Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    # PASO 1
    if st.button("🚀 PASO 1: REPORTE DE MEDIOS"):
        # (Aquí iría tu función de scraping_fiel de la respuesta anterior)
        # st.session_state.datos_medios = ... 
        st.write("Medios procesados...") # Marcador de posición
        
    # PASO 2
    if st.session_state.datos_medios and st.button("📱 PASO 2: AGREGAR RRSS"):
        # st.session_state.datos_rrss = ...
        st.write("RRSS procesadas...") # Marcador de posición

    # EXPORTACIÓN
    if st.session_state.reporte_final:
        st.subheader("💾 PASO 3: EXPORTAR")
        c1, c2 = st.columns(2)
        with c1:
            data_cbba = generar_word_oficial(st.session_state.reporte_final, "CBBA")
            st.download_button("Word CBBA", data_cbba, f"Reporte_CBBA_{fecha_hoy}.docx")
        with c2:
            data_scz = generar_word_oficial(st.session_state.reporte_final, "STACRUZ")
            st.download_button("Word STACRUZ", data_scz, f"Reporte_SCZ_{fecha_hoy}.docx")
else:
    st.warning("Por favor, introduce tu API Key en la izquierda.")
