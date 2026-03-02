import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import time

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")

# --- LÓGICA DE TIEMPO BOLIVIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
dia_semana = ahora.weekday() 
hora_actual = ahora.hour

if dia_semana == 0 and hora_actual < 12:
    rango_dias = "del sábado, domingo y lunes (Matutino)"
    fecha_ref = f"Noticias desde el {(ahora - timedelta(days=2)).strftime('%d/%m/%Y')} al {ahora.strftime('%d/%m/%Y')}"
    prompt_regla = "Incluye noticias relevantes desde el sábado pasado hasta hoy."
else:
    rango_dias = f"exclusivamente de hoy {ahora.strftime('%d/%m/%Y')} (Vespertino)"
    fecha_ref = f"Noticias de hoy {ahora.strftime('%d/%m/%Y')}"
    prompt_regla = "SOLO incluye noticias publicadas HOY lunes. Ignora días anteriores."

st.title(f"📰 MONITOREO DE NOTICIAS: {ahora.strftime('%d/%m/%Y')}")
st.info(f"Filtro activo: {rango_dias}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_noticias():
    fuentes = [
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/", "base": "https://www.opinion.com.bo"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/", "base": "https://www.lostiempos.com"},
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/", "base": "https://lavozdetarija.com"},
        {"nombre": "UNITEL", "url": "https://unitel.bo/economia/", "base": "https://unitel.bo"},
        {"nombre": "RED UNO", "url": "https://www.reduno.com.bo/", "base": "https://www.reduno.com.bo"},
        {"nombre": "ATB", "url": "https://www.atb.com.bo/", "base": "https://www.atb.com.bo"},
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/principal/", "base": "https://www.boliviatv.bo"},
        {"nombre": "URGENTE BO", "url": "https://www.urgente.bo/", "base": "https://www.urgente.bo"},
        {"nombre": "BOLIVISION", "url": "https://www.redbolivision.tv.bo/", "base": "https://www.redbolivision.tv.bo"},
        {"nombre": "CADENA A", "url": "https://www.cadenaa.tv/", "base": "https://www.cadenaa.tv"},
        {"nombre": "IN NOTICIAS", "url": "https://innoticiasbo.com/", "base": "https://innoticiasbo.com"},
        {"nombre": "ENFOQUE NEWS", "url": "https://enfoquenews.com.bo/", "base": "https://enfoquenews.com.bo"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    data_raw = ""
    pb = st.progress(0)
    for i, fuente in enumerate(fuentes):
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            limite = 10 if hora_actual >= 12 else 20
            for tag in soup.find_all(['h1', 'h2', 'h3'], limit=limite):
                titulo = tag.get_text().strip()
                a_tag = tag.find('a') or tag.find_parent('a')
                if a_tag and a_tag.get('href') and len(titulo) > 30:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'].rstrip('/') + link
                    data_raw += f"MEDIO: {fuente['nombre']} | TEMA: {titulo} | LINK: {full_link}\n"
        except: continue
    pb.empty()
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    
    if st.button('🚀 GENERAR MONITOREO'):
        modelo_valido = None
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'gemini-1.5-flash' in m.name:
                        modelo_valido = m.name
                        break
            if not modelo_valido:
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        modelo_valido = m.name
                        break
        except: pass

        if modelo_valido:
            noticias_raw = extraer_noticias()
            if len(noticias_raw) > 300:
                status_ia = st.empty()
                try:
                    status_ia.text(f"⚖️ IA analizando noticias...")
                    model = genai.GenerativeModel(modelo_valido)
                    
                    prompt = f"""
                    FECHA DEL REPORTE: {fecha_ref}.
                    {prompt_regla}
                    TAREA: Resumen técnico informativo. 
                    FORMATO: Solo texto plano, sin asteriscos ni negritas de Markdown.
                    ENTRADA: {noticias_raw}

                    ORDEN DE SALIDA:
                    TITULAR (MAYÚSCULAS)
                    MEDIO (MAYÚSCULAS)
                    Párrafo informativo de 5 líneas.
                    URL
                    (Deja exactamente dos saltos de línea entre cada noticia).
                    """
                    
                    response = model.generate_content(prompt
