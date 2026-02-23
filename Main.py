import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# Configuración de página
st.set_page_config(page_title="Reporte Bolivia Multi-Medio", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

st.title(f"📰 REPORTE DE NOTICIAS: {fecha_hoy}")
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
        {"nombre": "OPINIÓN COCHABAMBA", "url": "https://www.opinion.com.bo/", "base": "https://www.opinion.com.bo"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/", "base": "https://www.lostiempos.com"},
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/", "base": "https://lavozdetarija.com"},
        {"nombre": "UNITEL", "url": "https://unitel.bo/economia/", "base": "https://unitel.bo"},
        {"nombre": "RED UNO", "url": "https://www.reduno.com.bo/", "base": "https://www.reduno.com.bo"},
        {"nombre": "ATB DIGITAL", "url": "https://www.atb.com.bo/", "base": "https://www.atb.com.bo"},
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/principal/noticias", "base": "https://www.boliviatv.bo"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    data_acumulada = ""

    for fuente in fuentes:
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            # Buscamos titulares en etiquetas h1, h2, h3
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
    if st.button('🚀 GENERAR REPORTE COMPLETO'):
        with st.spinner('Analizando prensa y medios audiovisuales...'):
            modelo = detectar_modelo(api_key)
            noticias_raw = extraer_noticias()
            
            if len(noticias_raw) > 300:
                prompt = f"""
                Hoy es {fecha_hoy}. Actúa como un editor de prensa boliviano.
                Usa exclusivamente estos datos: {noticias_raw}
                
                TAREA: Genera 6 noticias sobre Economía, Impuestos y Política.
                PRIORIDAD: 1. Cochabamba, 2. Tarija, 3. Nacional.

                FORMATO ESTRICTO (Sigue esto sin añadir nada más):
                **TITULAR EN MAYÚSCULAS Y NEGRITA**
                **MEDIO EN MAYÚSCULAS Y NEGRITA**
                resumen detallado en minúsculas de 3 a 4 líneas.
                url completa en minúsculas
                
                (IMPORTANTE: Un salto de línea entre cada dato del bloque y un espacio entre noticias distintas. No uses la palabra "Resumen" ni "Enlace").
                """
                
                url_api = f"https://generativelanguage.googleapis.com/v1beta/{modelo}:generateContent?key={api_key}"
                res = requests.post(url_api, json={"contents": [{"parts": [{"text": prompt}]}]})
                
                if res.status_code == 200:
                    st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                else:
                    st.error("Error en el procesamiento de la IA.")
            else:
                st.error("No se pudo obtener información suficiente. Intenta nuevamente en unos segundos.")
else:
    st.warning("👈 Ingresa tu API Key en la barra lateral.")
