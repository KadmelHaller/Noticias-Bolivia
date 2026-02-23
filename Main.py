import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

st.set_page_config(page_title="Reporte Cochabamba 2026", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

st.title(f"📰 REPORTE COCHABAMBA: {fecha_hoy}")
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
        return "models/gemini-1.5-flash" # Fallback
    except: return "models/gemini-1.5-flash"

def extraer_cochabamba():
    # Prioridad absoluta a Cochabamba
    fuentes = [
        {"nombre": "Opinión Cochabamba", "url": "https://www.opinion.com.bo/section/cochabamba/", "base": "https://www.opinion.com.bo"},
        {"nombre": "Los Tiempos Economía", "url": "https://www.lostiempos.com/actualidad/economia", "base": "https://www.lostiempos.com"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    data_acumulada = ""

    for fuente in fuentes:
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            # Buscamos específicamente los links de noticias
            for tag in soup.find_all(['h1', 'h2', 'h3'], limit=12):
                titulo = tag.get_text().strip()
                a_tag = tag.find('a') or tag.find_parent('a')
                if a_tag and a_tag.get('href') and len(titulo) > 20:
                    link = a_tag['href']
                    # Corrección de enlaces relativos
                    full_link = link if link.startswith('http') else fuente['base'] + link
                    data_acumulada += f"Fuente: {fuente['nombre']} | Noticia: {titulo} | URL: {full_link}\n"
        except: continue
    return data_acumulada

if api_key:
    if st.button('🚀 GENERAR REPORTE COCHABAMBA'):
        with st.spinner('Analizando prensa de Cochabamba...'):
            modelo = detectar_modelo(api_key)
            noticias_cba = extraer_cochabamba()
            
            if len(noticias_cba) > 100:
                prompt = f"""
                Hoy es {fecha_hoy}. 
                DATOS REALES EXTRAÍDOS:
                {noticias_cba}
                
                INSTRUCCIÓN:
                Genera 6 bloques de noticias centrados exclusivamente en COCHABAMBA y BOLIVIA.
                Temas: Economía, Impuestos y Política.
                
                IMPORTANTE: 
                - Copia el enlace (URL) exactamente como aparece en los datos.
                - No inventes enlaces.
                
                FORMATO:
                **TITULAR: [TEXTO]**
                **MEDIO: [NOMBRE]**
                Resumen: [3 líneas]
                Enlace: [URL]
                """
                
                url_api = f"https://generativelanguage.googleapis.com/v1beta/{modelo}:generateContent?key={api_key}"
                res = requests.post(url_api, json={"contents": [{"parts": [{"text": prompt}]}]})
                
                if res.status_code == 200:
                    st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                else:
                    st.error("Error al generar el texto.")
            else:
                st.error("No se pudo leer la prensa de Cochabamba. Intenta de nuevo.")
