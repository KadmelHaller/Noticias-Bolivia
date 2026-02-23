import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# 1. Configuración de la interfaz
st.set_page_config(page_title="Reporte Bolivia Pro", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

st.title(f"📰 REPORTE AUTOMATIZADO: {fecha_hoy}")
st.markdown("Extrayendo noticias reales de Cochabamba, Tarija y Bolivia.")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

# 2. Función para obtener enlaces y textos reales (Scraping)
def obtener_noticias_reales():
    urls_fuente = [
        "https://www.opinion.com.bo/section/cochabamba/",
        "https://www.lostiempos.com/actualidad/economia",
        "https://lavozdetarija.com/category/tarija/politica/",
        "https://unitel.bo/economia/"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    buffer_noticias = ""
    
    for url in urls_fuente:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            # Buscamos artículos y sus enlaces reales
            articulos = soup.find_all(['h1', 'h2', 'h3'], limit=10)
            
            buffer_noticias += f"\n--- FUENTE: {url} ---\n"
            for art in articulos:
                titulo = art.get_text().strip()
                enlace = art.find('a')['href'] if art.find('a') else url
                # Asegurar que el enlace sea completo
                if enlace.startswith('/'):
                    base = url.split('/')[2]
                    enlace = f"https://{base}{enlace}"
                buffer_noticias += f"TITULO: {titulo} | LINK: {enlace}\n"
        except:
            continue
    return buffer_noticias

# 3. Función de conexión directa a la API (Evita error 404)
def llamar_gemini_v1(key, prompt):
    endpoint = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2} # Temperatura baja para mayor precisión
    }
    
    response = requests.post(endpoint, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        return f"Error en API: {response.text}"

# 4. Lógica de ejecución
if api_key:
    if st.button('🚀 GENERAR REPORTE CON ENLACES REALES'):
        with st.spinner('Escaneando portales de noticias bolivianos...'):
            datos_vivos = obtener_noticias_reales()
            
            if len(datos_vivos) > 100:
                prompt_instruccion = f"""
                Hoy es {fecha_hoy}. Actúa como editor. 
                A continuación te doy una lista de TITULOS y ENLACES extraídos hace un segundo de la web.
                
                TAREA: Selecciona las 6 noticias más relevantes sobre ECONOMÍA, IMPUESTOS o POLÍTICA.
                
                DATOS REALES:
                {datos_vivos}
                
                FORMATO DE SALIDA (SIN PREÁMBULOS):
                **TITULAR: [COPIAR TITULO FIELMENTE]**
                **MEDIO: [NOMBRE DEL MEDIO SEGÚN EL LINK]**
                Resumen: [Redacta un resumen de 3 líneas basado en el título y contexto de hoy]
                Enlace: [COPIAR EL LINK REAL PROPORCIONADO]
                """
                
                resultado = llamar_gemini_v1(api_key, prompt_instruccion)
                st.success("✅ Reporte finalizado.")
                st.markdown(resultado)
            else:
                st.error("No se pudo leer la información de los portales. Revisa tu conexión.")
else:
    st.warning("👈 Ingresa tu API Key para comenzar.")
