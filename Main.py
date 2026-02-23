import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# Configuración
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
        # Extraemos titulares y párrafos para que la IA tenga materia prima
        textos = [t.get_text() for t in soup.find_all(['h1', 'h2', 'p'])]
        return "\n".join(textos[:30]) # Enviamos los primeros 30 fragmentos
    except:
        return ""

if api_key:
    genai.configure(api_key=api_key)
    # Usamos el modelo base que es el más estable
    model = genai.GenerativeModel('gemini-1.5-flash')

    if st.button('🚀 GENERAR RESUMEN AHORA'):
        with st.spinner('Extrayendo datos de Opinión, Los Tiempos y La Voz...'):
            
            # Fuentes de donde sacaremos la información cruda
            urls = [
                "https://www.opinion.com.bo/section/cochabamba/",
                "https://www.lostiempos.com/actualidad/economia",
                "https://lavozdetarija.com/category/tarija/politica/"
            ]
            
            contenido_crudo = ""
            for u in urls:
                contenido_crudo += f"\n--- CONTENIDO DE: {u} ---\n"
                contenido_crudo += extraer_texto_web(u)

            if len(contenido_crudo) > 100:
                prompt = f"""
                Hoy es {fecha_hoy}. Te proporciono el contenido extraído de los portales de noticias de Bolivia.
                Tu tarea es leer este contenido y extraer las 6 noticias más importantes de ECONOMÍA, IMPUESTOS y POLÍTICA.

                DATOS EXTRAÍDOS:
                {contenido_crudo}

                FORMATO DE SALIDA (ESTRICTO PARA WORD):
                **TITULAR: [TITULAR EN MAYÚSCULAS Y NEGRITA]**
                **MEDIO: [MEDIO EN MAYÚSCULAS Y NEGRITA]**
                Resumen: [3 a 4 líneas de análisis basado en el texto]
                Enlace: https://en.wikipedia.org/wiki/Luis_de_la_Fuente_%28footballer,_born_1961%29

                Si el texto extraído no contiene noticias de hoy, indícalo, pero intenta resumir lo más reciente.
                """
                
                try:
                    response = model.generate_content(prompt)
                    st.success("Resumen generado exitosamente")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error al resumir: {e}")
            else:
                st.error("No se pudo extraer contenido de las webs. Revisa tu conexión.")
else:
    st.warning("👈 Ingresa tu API Key.")
