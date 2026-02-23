import streamlit as st
import google.generativeai as genai
from google.generativeai import types
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# Configuración de la página
st.set_page_config(page_title="Noticias Bolivia Hoy", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

st.title(f"📰 RESUMEN REAL: {fecha_hoy}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_texto_web(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        textos = [t.get_text() for t in soup.find_all(['h1', 'h2', 'p'])]
        return "\n".join(textos[:30])
    except:
        return ""

if api_key:
    try:
        # --- PARCHE DE CONEXIÓN ---
        # Forzamos la configuración para evitar la ruta v1beta
        genai.configure(api_key=api_key, transport='rest') 
        
        # Inicializamos el modelo de forma estándar
        model = genai.GenerativeModel('gemini-1.5-flash')

        if st.button('🚀 GENERAR RESUMEN AHORA'):
            with st.spinner('Extrayendo datos de portales bolivianos...'):
                
                urls = [
                    "https://www.opinion.com.bo/section/cochabamba/",
                    "https://www.lostiempos.com/actualidad/economia",
                    "https://lavozdetarija.com/category/tarija/politica/"
                ]
                
                contenido_crudo = ""
                for u in urls:
                    contenido_crudo += f"\n--- FUENTE: {u} ---\n"
                    contenido_crudo += extraer_texto_web(u)

                if len(contenido_crudo) > 100:
                    prompt = f"""
                    Hoy es {fecha_hoy}. Actúa como un editor de noticias.
                    Basándote EXCLUSIVAMENTE en el texto extraído que te paso abajo, resume las 6 noticias más importantes de ECONOMÍA, IMPUESTOS y POLÍTICA en Bolivia (Cochabamba/Tarija).

                    TEXTO EXTRAÍDO:
                    {contenido_crudo}

                    FORMATO DE SALIDA (PARA WORD):
                    **TITULAR: [TITULAR EN MAYÚSCULAS Y NEGRITA]**
                    **MEDIO: [NOMBRE DEL MEDIO EN MAYÚSCULAS]**
                    Resumen: [3 a 4 líneas de análisis real]
                    Enlace: https://www.spanishdict.com/translate/de%20la%20fuente
                    """
                    
                    # Intentamos generar el contenido
                    response = model.generate_content(prompt)
                    st.success("✅ Resumen generado exitosamente")
                    st.markdown(response.text)
                else:
                    st.error("No se pudo extraer contenido de las webs. Verifica los enlaces.")

    except Exception as e:
        st.error("Error de configuración de la IA.")
        st.info(f"Detalle técnico: {e}")
else:
    st.warning("👈 Ingresa tu API Key en la barra lateral.")
