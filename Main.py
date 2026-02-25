import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

st.set_page_config(page_title="Reporte Bolivia Profesional", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO DE NOTICIAS - SIN CBBA: {fecha_hoy}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def detectar_modelo(key):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(url)
        if res.status_code == 200:
            modelos = res.json().get('models', [])
            for m in modelos:
                if "flash" in m['name'] and "generateContent" in m['supportedGenerationMethods']:
                    return m['name']
        return "models/gemini-1.5-flash"
    except: return "models/gemini-1.5-flash"

def extraer_noticias():
    fuentes = [
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/", "base": "https://www.opinion.com.bo"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/", "base": "https://www.lostiempos.com"},
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/", "base": "https://lavozdetarija.com"},
        {"nombre": "UNITEL", "url": "https://unitel.bo/economia/", "base": "https://unitel.bo"},
        {"nombre": "RED UNO", "url": "https://www.reduno.com.bo/", "base": "https://www.reduno.com.bo"},
        {"nombre": "ATB", "url": "https://www.atb.com.bo/", "base": "https://www.atb.com.bo"},
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/", "base": "https://www.boliviatv.bo"}
        {"nombre": "URGENTE BO", "url": "https://www.urgente.bo/", "base": "https://www.urgente.bo/"}
        {"nombre": "BOLIVISION", "url": "https://www.redbolivision.tv.bo/", "base": "https://www.redbolivision.tv.bo/"}
        {"nombre": "CADENA A", "url": "https://www.cadenaa.tv/", "base": "https://www.cadenaa.tv/"}
        {"nombre": "IN NOTICIAS", "url": "https://innoticiasbo.com/", "base": "https://innoticiasbo.com/"}
        {"nombre": "ENFOQUE NEWS", "url": "https://enfoquenews.com.bo/", "base": "https://enfoquenews.com.bo/"}

    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    data_acumulada = ""

    for fuente in fuentes:
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            for tag in soup.find_all(['h1', 'h2', 'h3'], limit=8):
                titulo = tag.get_text().strip()
                a_tag = tag.find('a') or tag.find_parent('a')
                if a_tag and a_tag.get('href') and len(titulo) > 25:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'] + link
                    data_acumulada += f"Fuente: {fuente['nombre']} | Noticia: {titulo} | URL: {full_link}\n"
        except: continue
    return data_acumulada

if api_key:
    if st.button('🚀 GENERAR MONITOREO'):
        with st.spinner('Analizando medios...'):
            modelo = detectar_modelo(api_key)
            noticias_raw = extraer_noticias()
            
            if len(noticias_raw) > 300:
                # Prompt con instrucciones de formato negativas (prohibiciones)
                prompt = f"""
                Hoy es {fecha_hoy}. Actúa como editor. Datos: {noticias_raw}
                
                Instrucciones Críticas de Formato:
                1. Entrega noticias (Prioriza Cochabamba, luego Tarija, luego TV nacional, solamente noticias sobre economía, impuestos y gobierno).
                2. NO uses las etiquetas "Titular", "Medio", "Resumen" o "Enlace". Prohibido poner etiquetas.
                3. Cada bloque de noticia debe tener exactamente 4 datos directos sin etiqueta separados por saltos de línea simples:
                   Línea 1: EL TITULAR EN MAYÚSCULAS Y NEGRITA y luego un salto de línea.
                   Línea 2: EL NOMBRE DEL MEDIO EN MAYÚSCULAS Y NEGRITA y luego un salto de línea.
                   Línea 3: resumen de 4 a 6 líneas, párrafo normal y luego un salto de línea.
                   Línea 4: url completa en minúsculas.
                4. Separa cada una de las 4 líneas con un salto de línea simple de forma tal que no se confunda la información.
                5. Deja dos saltos de línea entre cada bloque de noticia.
                6. Verifica cada nombre y cargo mencionado en las noticias para que el resumen tenga datos correctos.
                """
                
                url_api = f"https://generativelanguage.googleapis.com/v1beta/{modelo}:generateContent?key={api_key}"
                res = requests.post(url_api, json={"contents": [{"parts": [{"text": prompt}]}]})
                
                if res.status_code == 200:
                    # Usamos st.text para que no interprete Markdown extraño y respete saltos
                    st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                else:
                    st.error("Error en el procesamiento.")
 
