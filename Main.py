import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

st.set_page_config(page_title="Reporte Bolivia Final", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

st.title(f"📰 REPORTE BOLIVIA: {fecha_hoy}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def obtener_modelo_valido(key):
    # Esta función le pregunta a Google qué modelos puedes usar tú
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    response = requests.get(url)
    if response.status_code == 200:
        models = response.json().get('models', [])
        for m in models:
            if "generateContent" in m.get('supportedGenerationMethods', []):
                return m['name'] # Retorna el primer modelo válido que encuentre
    return None

def extraer_datos():
    fuentes = [
        "https://www.opinion.com.bo/section/cochabamba/",
        "https://www.lostiempos.com/actualidad/economia",
        "https://lavozdetarija.com/category/tarija/politica/"
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    datos = ""
    for url in fuentes:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            articulos = soup.find_all(['h1', 'h2', 'h3'], limit=5)
            for art in articulos:
                texto = art.get_text().strip()
                link = art.find('a')['href'] if art.find('a') else url
                if link.startswith('/'):
                    link = f"https://{url.split('/')[2]}{link}"
                datos += f"Noticia: {texto} | Link: {link}\n"
        except: continue
    return datos

if api_key:
    if st.button('🚀 GENERAR REPORTE AHORA'):
        with st.spinner('Detectando modelo y noticias...'):
            # 1. Detectamos qué modelo tienes tú
            nombre_modelo = obtener_modelo_valido(api_key)
            
            if nombre_modelo:
                # 2. Extraemos noticias
                contexto = extraer_datos()
                
                # 3. Llamada a la API con el nombre de modelo autodetectado
                url_api = f"https://generativelanguage.googleapis.com/v1beta/{nombre_modelo}:generateContent?key={api_key}"
                prompt = f"Hoy es {fecha_hoy}. Resume estas noticias en 6 bloques con Titular, Medio, Resumen y Enlace Real: {contexto}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                
                res = requests.post(url_api, json=payload)
                if res.status_code == 200:
                    st.success(f"Modelo detectado y usado: {nombre_modelo}")
                    st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                else:
                    st.error(f"Error al generar: {res.text}")
            else:
                st.error("No se encontraron modelos disponibles para esta API Key.")
