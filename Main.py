import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# 1. Configuración de la página
st.set_page_config(page_title="Reporte Bolivia 2026", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

st.title(f"📰 RESUMEN REAL BOLIVIA: {fecha_hoy}")

# 2. Barra lateral para API Key
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_texto_web(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        textos = [t.get_text() for t in soup.find_all(['h1', 'h2', 'p'])]
        return "\n".join(textos[:25])
    except:
        return ""

def llamar_gemini_directo(key, prompt):
    # Forzamos la URL a la versión estable V1, evitando la V1BETA
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")

# 3. Lógica principal
if api_key:
    if st.button('🚀 GENERAR REPORTE DE HOY'):
        with st.spinner('Leyendo portales: Opinión, Los Tiempos y La Voz...'):
            
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
                prompt_final = f"""
                Hoy es {fecha_hoy}. Actúa como un editor de noticias senior.
                A continuación te paso el texto extraído de los diarios de hoy en Bolivia. 
                Extrae las 6 noticias más importantes de ECONOMÍA, IMPUESTOS y POLÍTICA.

                TEXTO EXTRAÍDO:
                {contenido_crudo}

                FORMATO DE SALIDA (ESTRICTO PARA COPIAR A WORD):
                **TITULAR: [MAYÚSCULAS Y NEGRITA]**
                **MEDIO: [NOMBRE DEL MEDIO]**
                Resumen: [3 a 4 líneas de análisis real]
                Enlace: https://en.wikipedia.org/wiki/Luis_de_la_Fuente_%28footballer,_born_1961%29
                """
                
                try:
                    resultado = llamar_gemini_directo(api_key, prompt_final)
                    st.success("✅ Resumen generado exitosamente")
                    st.markdown(resultado)
                except Exception as e:
                    st.error("Error al conectar con la API de Google.")
                    st.info(f"Detalle técnico: {e}")
            else:
                st.error("No se pudo extraer información de los periódicos. Intenta más tarde.")
else:
    st.warning("👈 Ingresa tu API Key en la barra lateral.")
