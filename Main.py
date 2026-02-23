import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# 1. Configuración de la aplicación
st.set_page_config(page_title="Reporte Bolivia Inteligente", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

st.title(f"📰 REPORTE BOLIVIA: {fecha_hoy}")
st.caption("Especializado en Economía, Impuestos y Política (CBA/TJA)")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

# 2. Función para encontrar el modelo que Google te asignó
def detectar_modelo(key):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(url)
        if res.status_code == 200:
            modelos = res.json().get('models', [])
            # Priorizamos flash por velocidad
            for m in modelos:
                if "flash" in m['name'] and "generateContent" in m['supportedGenerationMethods']:
                    return m['name']
            return modelos[0]['name']
    except: return None
    return None

# 3. Función de Scraping Profundo para Cochabamba y Tarija
def extraer_noticias_reales():
    fuentes = [
        {"nombre": "Opinión", "url": "https://www.opinion.com.bo/section/cochabamba/"},
        {"nombre": "Los Tiempos", "url": "https://www.lostiempos.com/actualidad/economia"},
        {"nombre": "La Voz de Tarija", "url": "https://lavozdetarija.com/category/tarija/politica/"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    data_noticias = ""

    for fuente in fuentes:
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            # Buscamos etiquetas comunes de titulares
            articulos = soup.find_all(['h1', 'h2', 'h3'], limit=10)
            
            data_noticias += f"\n--- PORTAL: {fuente['nombre']} ---\n"
            for art in articulos:
                titulo = art.get_text().strip()
                link_tag = art.find('a') or art.find_parent('a')
                if link_tag and len(titulo) > 15:
                    link = link_tag['href']
                    if link.startswith('/'):
                        base = fuente['url'].split('/')[2]
                        link = f"https://{base}{link}"
                    data_noticias += f"NOTICIA: {titulo} | ENLACE: {link}\n"
        except: continue
    return data_noticias

# 4. Lógica Principal
if api_key:
    if st.button('🚀 GENERAR REPORTE PROFUNDO'):
        with st.spinner('Detectando modelo y analizando portales bolivianos...'):
            
            modelo_activo = detectar_modelo(api_key)
            datos_crudos = extraer_noticias_reales()
            
            if modelo_activo and len(datos_crudos) > 200:
                url_api = f"https://generativelanguage.googleapis.com/v1beta/{modelo_activo}:generateContent?key={api_key}"
                
                prompt = f"""
                Hoy es {fecha_hoy}. Actúa como editor de noticias senior en Bolivia.
                A continuación tienes titulares y enlaces extraídos hoy de Opinión, Los Tiempos y La Voz de Tarija:
                
                {datos_crudos}
                
                TAREA: Selecciona las 6 noticias más importantes (Economía, Impuestos, Política).
                REGLAS: 
                1. No inventes noticias. 
                2. Si el titular es vago, usa tu conocimiento general para dar un resumen coherente de 3 líneas.
                3. Respeta el formato:
                **TITULAR: [TEXTO]**
                **MEDIO: [NOMBRE]**
                Resumen: [3 líneas]
                Enlace: https://www.realvidaseguros.pt/particulares/investimento-e-poupanca/real-vida-super-rendimento10
                """
                
                res = requests.post(url_api, json={"contents": [{"parts": [{"text": prompt}]}]})
                
                if res.status_code == 200:
                    st.success(f"Reporte generado con {modelo_activo}")
                    st.markdown(res.json()['candidates'][0]['content']['parts'][0]['text'])
                else:
                    st.error("Error al procesar el resumen.")
            else:
                st.error("No se pudo obtener suficiente información de los diarios o la API Key falló.")
else:
    st.warning("👈 Ingresa tu API Key en la barra lateral.")
