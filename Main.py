import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# 1. Configuración
st.set_page_config(page_title="Reporte Bolivia Final", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

st.title(f"📰 REPORTE BOLIVIA: {fecha_hoy}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

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
            articulos = soup.find_all(['h1', 'h2', 'h3'], limit=8)
            for art in articulos:
                texto = art.get_text().strip()
                link = art.find('a')['href'] if art.find('a') else url
                if link.startswith('/'):
                    link = f"https://{url.split('/')[2]}{link}"
                datos += f"Noticia: {texto} | Link: {link}\n"
        except: continue
    return datos

def llamar_api(key, prompt):
    # Intentamos con 'gemini-1.5-flash-latest' que es el nombre global de producción
    # Si este falla, el error nos dirá exactamente qué nombre usar.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        # Intento de rescate con modelo Pro si el Flash falla
        url_alt = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={key}"
        response_alt = requests.post(url_alt, headers=headers, json=payload)
        if response_alt.status_code == 200:
            return response_alt.json()['candidates'][0]['content']['parts'][0]['text']
        return f"Error crítico de Google: {response_alt.text}"

if api_key:
    if st.button('🚀 GENERAR REPORTE AHORA'):
        with st.spinner('Obteniendo noticias reales...'):
            contexto = extraer_datos()
            if contexto:
                instruccion = f"""
                Hoy es {fecha_hoy}. Basado en estos datos REALES:
                {contexto}
                
                Genera 6 noticias de Economía, Impuestos o Política. 
                USA ESTE FORMATO:
                **TITULAR: [TEXTO]**
                **MEDIO: [NOMBRE]**
                Resumen: [3 líneas]
                Enlace: [LINK REAL]
                """
                resultado = llamar_api(api_key, instruccion)
                st.markdown(resultado)
            else:
                st.error("No se pudo leer información de los diarios.")
else:
    st.warning("Ingresa tu API Key.")
