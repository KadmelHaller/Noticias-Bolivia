import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from io import BytesIO
import time
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
import docx.opc.constants

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Estratégico Bolivia", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

KEYWORDS_STRICT = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "gobierno", "arce", "ministro", "economia", "dolar", "banco", "subvención", "combustible", "bolivia", "presupuesto"]

if 'reporte_final' not in st.session_state: st.session_state.reporte_final = ""

# --- 2. FUNCIONES DE WORD (Interlineado 0 y Links Azules) ---

def añadir_hipervinculo(paragraph, url):
    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    hyperlink = docx.oxml.shared.OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)
    new_run = docx.oxml.shared.OxmlElement('w:r')
    rPr = docx.oxml.shared.OxmlElement('w:rPr')
    c = docx.oxml.shared.OxmlElement('w:color'); c.set(qn('w:val'), '0000FF')
    u = docx.oxml.shared.OxmlElement('w:u'); u.set(qn('w:val'), 'single')
    rPr.append(c); rPr.append(u)
    new_run.append(rPr)
    t = docx.oxml.shared.OxmlElement('w:t'); t.text = url
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)

def generar_word_oficial(texto, ciudad_tag):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(10)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.line_spacing = 1.0

    section = doc.sections[0]
    section.header.paragraphs[0].add_run("\n\n")
    doc.add_paragraph("N°")
    doc.add_paragraph(fecha_hoy)
    doc.add_paragraph("Reporte Estratégico")
    doc.add_paragraph("")

    target = "COCHABAMBA" if ciudad_tag == "CBBA" else "SANTA CRUZ"
    lineas = texto.split('\n')
    capturando = False
    
    for linea in lineas:
        l_upper = linea.upper().strip()
        if target in l_upper and any(p in l_upper for p in ["1.", "2."]):
            capturando = True
            continue
        if capturando and any(p in l_upper for p in ["1.", "2."]) and target not in l_upper:
            capturando = False

        if capturando and linea.strip():
            if "HTTP" in linea.upper():
                p = doc.add_paragraph()
                añadir_hipervinculo(p, linea.strip())
                doc.add_paragraph("") 
            else:
                p = doc.add_paragraph()
                if "*" in linea:
                    run = p.add_run(linea.replace('*', '').strip().upper()); run.bold = True
                elif any(m in l_upper for m in ["OPINIÓN", "EL DEBER", "UNITEL", "RED UNO", "LA VOZ", "VISIÓN 360", "LOS TIEMPOS"]):
                    run = p.add_run(l_upper); run.bold = True
                else:
                    p.add_run(linea)
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

# --- 3. PROCESAMIENTO E IA POR LOTES (Anti-429) ---

def llamar_ia_segura(datos_batch):
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = next((m for m in modelos if "flash" in m), modelos[0])
        model = genai.GenerativeModel(target_model)
        
        prompt = f"FECHA: {fecha_hoy}. Resume estas noticias de BOLIVIA para un reporte de IMPUESTOS/ECONOMÍA. Formato: *TITULAR*, MEDIO, Resumen 5 líneas, Enlace. Clasifica en 1. COCHABAMBA o 2. SANTA CRUZ."
        
        res = model.generate_content(prompt + "\n\nNOTICIAS:\n" + datos_batch)
        return res.text
    except Exception as e:
        if "429" in str(e):
            time.sleep(20) # Pausa si hay saturación
            return llamar_ia_segura(datos_batch) # Reintenta una vez
        return ""

# --- 4. INTERFAZ ---

st.title(f"🔍 MONITOR ESTRATÉGICO: {fecha_hoy}")
api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    if st.button("🚀 INICIAR MONITOREO"):
        fuentes = [
            {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba"},
            {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "r": "Cochabamba"},
            {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "r": "Santa Cruz"},
            {"n": "LA VOZ DIGITAL", "u": "https://lavoz.digital/", "r": "Santa Cruz"},
            {"n": "VISIÓN 360", "u": "https://www.vision360.bo/", "r": "Nacional"}
        ]
        
        reporte_acumulado = ""
        progreso = st.progress(0)
        
        for idx, f in enumerate(fuentes):
            try:
                r = requests.get(f['u'], headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                soup = BeautifulSoup(r.text, 'html.parser')
                noticias_medio = ""
                
                for el in soup.find_all(['h1', 'h2', 'h3', 'a']):
                    tit = el.get_text().strip()
                    if len(tit) > 35 and any(k in tit.lower() for k in KEYWORDS_STRICT):
                        noticias_medio += f"MEDIO: {f['n']} | REGIÓN: {f['r']} | NOTICIA: {tit}\n"
                
                if noticias_medio:
                    # Procesamos cada medio de forma independiente para no saturar la cuota
                    resultado_parcial = llamar_ia_segura(noticias_medio)
                    reporte_acumulado += resultado_parcial + "\n\n"
                    time.sleep(2) # Pausa de seguridad entre llamadas
            except: continue
            progreso.progress((idx + 1) / len(fuentes))
        
        if reporte_acumulado:
            st.session_state.reporte_final = reporte_acumulado
            st.success("Completado.")
            st.text_area("Reporte:", st.session_state.reporte_final, height=400)
        else:
            st.warning("No se hallaron noticias hoy.")

    if st.session_state.reporte_final:
        c1, c2 = st.columns(2)
        with c1: st.download_button("Descargar Word CBBA", generar_word_oficial(st.session_state.reporte_final, "CBBA"), f"Reporte_CBBA_{fecha_hoy.replace('/','-')}.docx")
        with c2: st.download_button("Descargar Word SCZ", generar_word_oficial(st.session_state.reporte_final, "STACRUZ"), f"Reporte_SCZ_{fecha_hoy.replace('/','-')}.docx")
