import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_str = ahora.strftime('%A %d de %B de %Y') 

st.title(f"📰 MONITOREO DE NOTICIAS: {ahora.strftime('%d/%m/%Y')}")
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
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/principal/", "base": "https://www.boliviatv.bo"},
        {"nombre": "URGENTE BO", "url": "https://www.urgente.bo/", "base": "https://www.urgente.bo"},
        {"nombre": "BOLIVISION", "url": "https://www.redbolivision.tv.bo/", "base": "https://www.redbolivision.tv.bo"},
        {"nombre": "CADENA A", "url": "https://www.cadenaa.tv/", "base": "https://www.cadenaa.tv"},
        {"nombre": "IN NOTICIAS", "url": "https://innoticiasbo.com/", "base": "https://innoticiasbo.com"},
        {"nombre": "ENFOQUE NEWS", "url": "https://enfoquenews.com.bo/", "base": "https://enfoquenews.com.bo"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    data_acumulada = ""

    # Espacio para mostrar el progreso en la UI
    status_text = st.empty()
    
    for fuente in fuentes:
        # Actualiza el mensaje en la pantalla
        status_text.text(f"🔍 Consultando: {fuente['nombre']}...")
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            for tag in soup.find_all(['h1', 'h2', 'h3'], limit=10):
                titulo = tag.get_text().strip()
                a_tag = tag.find('a') or tag.find_parent('a')
                if a_tag and a_tag.get('href') and len(titulo) > 30:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'].rstrip('/') + link
                    data_acumulada += f"MEDIO: {fuente['nombre']} | TEMA: {titulo} | LINK: {full_link}\n"
        except: continue
    
    # Limpia el texto de estado al terminar
    status_text.empty()
    return data_acumulada

if api_key:
    if st.button('🚀 GENERAR MONITOREO SIN BLOQUEOS'):
        noticias_raw = extraer_noticias()
        
        with st.spinner('⚖️ Procesando información con IA...'):
            modelo = detectar_modelo(api_key)
            
            if len(noticias_raw) > 300:
                prompt = f"""
                FECHA DE REFERENCIA: {fecha_hoy_str}.
                TAREA: Extracción de datos de prensa para informe técnico.
                
                ENTRADA DE DATOS:
                {noticias_raw}
                
                REGLAS DE FILTRADO (OBLIGATORIAS):
                - Solo eventos del {fecha_hoy_str}.
                - Temas: Economía, Impuestos, Estado.
                - Orden: OPINIÓN, LOS TIEMPOS, LA VOZ DE TARIJA, TV, DIGITALES.

                FORMATO DE RESPUESTA (ESTRICTO):
                ** * TITULAR EN MAYÚSCULAS * **
                Salto de línea sencillo.
                **MEDIO EN MAYÚSCULAS**
                Salto de línea sencillo.
                Párrafo técnico informativo de 4 a 6 líneas sin usar lenguaje emocional.
                Salto de línea sencillo.
                URL en minúsculas.

                (Dos saltos de línea entre bloques. NO agregues introducciones ni conclusiones).
                """
                
                url_api = f"https://generativelanguage.googleapis.com/v1beta/{modelo}:generateContent?key={api_key}"
                
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "safetySettings": [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                    ],
                    "generationConfig": {"temperature": 0.0}
                }
                
                res = requests.post(url_api, json=payload)
                
                if res.status_code == 200:
                    try:
                        texto = res.json()['candidates'][0]['content']['parts'][0]['text']
                        st.markdown(texto)
                    except:
                        st.error("La IA bloqueó la respuesta por motivos de seguridad.")
                else:
                    st.error(f"Error: {res.status_code}")
