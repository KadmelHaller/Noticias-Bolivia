import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
import docx.opc.constants

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Estratégico Bolivia", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

KEYWORDS_STRICT = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "gobierno", "arce", "ministro", "economia", "dolar", "banco", "subvención", "combustible"]

if 'reporte_final' not in st.session_state: st.session_state.reporte_final = ""

# --- FUNCIONES TÉCNICAS DE WORD ---

def añadir_hipervinculo(paragraph, url):
    """Crea un enlace real en Word (Azul + Subrayado)"""
    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    hyperlink = docx.oxml.shared.OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)
    new_run = docx.oxml.shared.OxmlElement('w:r')
    rPr = docx.oxml.shared.OxmlElement('w:rPr')
    # Formato visual del link
    c = docx.oxml.shared.OxmlElement('w:color')
    c.set(qn('w:val'), '0000FF')
    u = docx.oxml.shared.OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(c)
    rPr.append(u)
    new_run.append(rPr)
    t = docx.oxml.shared.OxmlElement('w:t')
    t.text = url
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink

def generar_word_oficial(texto, ciudad_tag):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(10)
    
    # Interlineado y espaciado CERO absoluto
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.line_spacing = 1.0

    section = doc.sections[0]
    section.header.paragraphs[0].add_run("\n\n")

    doc.add_paragraph("N°")
    doc.add_paragraph(fecha_hoy)
    from datetime import datetime # Re-asegurar para la lógica de envío
    ahora = datetime.now(zona_horaria)
    hm = ahora.hour * 100 + ahora.minute
    envio = "1er Envío" if 830 <= hm <= 930 else "2do Envío" if 1330 <= hm <= 1430 else "3er Envío" if 1530 <= hm <= 1630 else "Envío Extraordinario"
    doc.add_paragraph(envio)
    doc.add_paragraph("") # Espacio tras encabezado

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
            # Si es un link, crear hipervínculo real
            if "http" in linea.lower():
                p = doc.add_paragraph()
                añadir_hipervinculo(p, linea.strip())
                doc.add_paragraph("") # SALTO DE LÍNEA SIMPLE ENTRE NOTICIAS
            else:
                p = doc.add_paragraph()
                if "*" in linea: # Titular
                    run = p.add_run(linea.replace('*', '').strip().upper())
                    run.bold = True
                elif any(m in l_upper for m in ["OPINIÓN", "EL DEBER", "UNITEL", "RED UNO", "LA VOZ", "VISIÓN 360", "LOS TIEMPOS", "ATB", "PAT"]):
                    run = p.add_run(l_upper)
                    run.bold = True
                else:
                    p.add_run(linea)

    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- PROCESAMIENTO E IA ---

def procesar_ia_robusta(datos_raw):
    try:
        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        nombre_modelo = next((m for m in modelos_disponibles if "1.5-flash" in m), modelos_disponibles[0])
        model = genai.GenerativeModel(nombre_modelo)
        
        prompt = f"""
        FECHA: {fecha_hoy}. 
        SOLO noticias de BOLIVIA sobre IMPUESTOS, ECONOMÍA y GOBIERNO. 
        ESTRUCTURA OBLIGATORIA:
        1. COCHABAMBA
        2. SANTA CRUZ
        FORMATO:
        *TITULAR EN MAYÚSCULAS*
        MEDIO EN MAYÚSCULAS
        Resumen de 5 líneas con nombres y cargos exactos. Sin etiquetas.
        Enlace directo en la última línea.
        """
        res = model.generate_content(prompt + "\n\nDATOS:\n" + datos_raw)
        return res.text
    except Exception as e:
        return f"Error: {str(e)}"

# --- INTERFAZ ---

st.title(f"🔍 MONITOR ESTRATÉGICO: {fecha_hoy}")
api_key = st.sidebar.text_input("Gemini API Key:", type="password")

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
        datos_crudos = ""
        for f in fuentes:
            try:
                r = requests.get(f['u'], headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                soup = BeautifulSoup(r.text, 'html.parser')
                for el in soup.find_all(['h1', 'h2', 'h3']):
                    tit = el.get_text().strip()
                    if len(tit) > 30 and any(k in tit.lower() for k in KEYWORDS_STRICT):
                        datos_crudos += f"MEDIO: {f['n']} | REGIÓN: {f['r']} | NOTICIA: {tit}\n"
            except: continue
        
        if datos_crudos:
            st.session_state.reporte_final = procesar_ia_robusta(datos_crudos)
            st.success("Listo.")

    if st.session_state.reporte_final:
        st.subheader("💾 EXPORTAR")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("Descargar Word CBBA", generar_word_oficial(st.session_state.reporte_final, "CBBA"), f"Reporte_CBBA_{fecha_hoy.replace('/','-')}.docx")
        with c2:
            st.download_button("Descargar Word STACRUZ", generar_word_oficial(st.session_state.reporte_final, "STACRUZ"), f"Reporte_STACRUZ_{fecha_hoy.replace('/','-')}.docx")
