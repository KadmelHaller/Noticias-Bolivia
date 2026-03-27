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
    
    rFonts = style.element.rPr.rFonts
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')

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
        if target in l_upper and any(prefix in l_upper for prefix in ["1.", "2.", "COCHABAMBA", "SANTA CRUZ"]):
            capturando = True
            continue
        other_target = "SANTA CRUZ" if target == "COCHABAMBA" else "COCHABAMBA"
        if capturando and other_target in l_upper and any(prefix in l_upper for prefix in ["1.", "2."]):
            capturando = False

        if capturando and linea.strip():
            p = doc.add_paragraph()
            if "*" in linea:
                limpia = linea.replace('*', '').strip().upper()
                run = p.add_run(limpia)
                run.bold = True
            elif any(m in l_upper for m in ["OPINIÓN", "EL DEBER", "UNITEL", "RED UNO", "LA VOZ", "VISIÓN 360", "LOS TIEMPOS", "ATB", "PAT", "INNOTICIAS", "ENFOQUE NEWS"]):
                run = p.add_run(l_upper)
                run.bold = True
            else:
                p.add_run(linea)
            p.paragraph_format.space_after = Pt(4)

    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. PROCESAMIENTO E IA (OPTIMIZADO PARA EVITAR CUOTAS AGOTADAS) ---

def procesar_ia_robusta(datos_raw):
    try:
        # 1. Obtener todos los modelos disponibles
        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 2. Priorizar 'gemini-1.5-flash' porque tiene la cuota gratuita más generosa
        # (15 peticiones por minuto vs las 2 o 3 de los modelos Pro)
        nombre_modelo = ""
        for m in modelos_disponibles:
            if "1.5-flash" in m:
                nombre_modelo = m
                break
        
        if not nombre_modelo:
            nombre_modelo = modelos_disponibles[0]

        model = genai.GenerativeModel(
