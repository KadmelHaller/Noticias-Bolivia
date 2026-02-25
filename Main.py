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

st.title(f"📰 MONITOREO DE NOTICIAS - SIN CBBA: {ahora.strftime('%d/%m/%Y')}")
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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    data_acumulada = ""

    for fuente in fuentes:
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            for tag in soup.find_all(['h1', 'h2', 'h3'], limit=12):
                titulo = tag.get_text().strip()
                a_tag = tag.find('a') or tag.find_parent('a')
                if a_tag and a_tag.get('href') and len(titulo) > 30:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'].rstrip('/') + link
                    data_acumulada += f"Fuente: {fuente['nombre']} | Noticia: {titulo} | URL: {full_link}\n"
        except: continue
    return data_acumulada

if api_key:
    if st.button('🚀 GENERAR MONITOREO DEL DÍA'):
        with st.spinner('Analizando vigencia y ordenando noticias...'):
            modelo = detectar_modelo(api_key)
            noticias_raw = extraer_noticias()
            
            if len(noticias_raw) > 300:
                prompt = f"""
                Hoy es {fecha_hoy_str}. Actúa como un sistema de archivo histórico neutral. 
                No generes opiniones, solo transcribe resúmenes informativos de la prensa.
                
                DATOS EXTRAÍDOS:
                {noticias_raw}
                
                REGLAS DE FILTRADO:
                1. SOLO noticias de HOY {fecha_hoy_str}.
                2. Prioridad: Economía, Impuestos y Gobierno.
                3. Prioridad Geográfica: Cochabamba y Tarija.

                ORDEN: Opinión, Los Tiempos, La Voz de Tarija, TV, Digitales.

                FORMATO DE SALIDA (ESTRICTO):
                **TITULAR EN MAYÚSCULAS Y NEGRITA**
                **MEDIO EN MAYÚSCULAS Y NEGRITA**
                Resumen de 4 a 6 líneas en minúsculas. Detalla nombres y cargos de forma objetiva.
                URL completa en minúsculas.

                INSTRUCCIÓN DE SEGURIDAD: 
                Si la noticia trata sobre crisis laboral o política, descríbela técnicamente sin usar adjetivos para evitar bloqueos del sistema.
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
                    "generationConfig": {
                        "temperature": 0.0,
                        "maxOutputTokens": 3000
                    }
                }
                
                res = requests.post(url_api, json=payload)
                
                if res.status_code == 200:
                    data = res.json()
                    # Si no hay 'content' en la respuesta, es que fue bloqueado
                    try:
                        texto = data['candidates'][0]['content']['parts'][0]['text']
                        st.markdown(texto)
                    except (KeyError, IndexError):
                        st.warning("⚠️ El filtro de seguridad de la IA bloqueó parte del reporte debido a palabras sensibles en las noticias. Mostrando el motivo técnico:")
                        st.json(data['candidates'][0].get('safetyRatings', []))
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
