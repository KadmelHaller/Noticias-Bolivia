import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import time

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
dia_semana = ahora.weekday() # 0 es Lunes

if dia_semana == 0:
    rango_dias = "del sábado, domingo y hoy lunes"
    fecha_referencia = f"HOY es {ahora.strftime('%d/%m/%Y')}, pero incluye noticias relevantes desde el sábado {(ahora - timedelta(days=2)).strftime('%d/%m/%Y')}"
else:
    rango_dias = "de hoy"
    fecha_referencia = f"HOY {ahora.strftime('%d/%m/%Y')}"

st.title(f"📰 MONITOREO DE NOTICIAS: {ahora.strftime('%d/%m/%Y')}")
st.info(f"Criterio de búsqueda: Noticias {rango_dias}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

# --- FUNCIÓN DE AUTODETECCIÓN DE MODELO ---
def obtener_ruta_modelo(key):
    try:
        # Consultamos la lista de modelos disponibles para esta KEY
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(url)
        if res.status_code == 200:
            modelos = res.json().get('models', [])
            # Buscamos el modelo flash más actual disponible
            for m in modelos:
                if "gemini-1.5-flash" in m['name']:
                    return m['name'] # Retorna la ruta completa "models/gemini-1.5-flash"
            # Si no hay 1.5, buscamos cualquier flash
            for m in modelos:
                if "flash" in m['name']:
                    return m['name']
        return "models/gemini-1.5-flash" # Default por si falla
    except:
        return "models/gemini-1.5-flash"

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

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_fuentes = len(fuentes)
    for i, fuente in enumerate(fuentes):
        porcentaje = int(((i + 1) / total_fuentes) * 100)
        status_text.text(f"🔍 [{porcentaje}%] Escaneando: {fuente['nombre']}...")
        progress_bar.progress((i + 1) / total_fuentes)
        
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            limite = 20 if dia_semana == 0 else 12
            for tag in soup.find_all(['h1', 'h2', 'h3'], limit=limite):
                titulo = tag.get_text().strip()
                a_tag = tag.find('a') or tag.find_parent('a')
                if a_tag and a_tag.get('href') and len(titulo) > 30:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'].rstrip('/') + link
                    data_acumulada += f"MEDIO: {fuente['nombre']} | TEMA: {titulo} | LINK: {full_link}\n"
        except: continue
    
    status_text.empty()
    progress_bar.empty()
    return data_acumulada

if api_key:
    if st.button('🚀 GENERAR MONITOREO'):
        noticias_raw = extraer_noticias()
        
        if len(noticias_raw) > 300:
            progress_ia = st.progress(0)
            status_ia = st.empty()
            
            for p in range(0, 96, 4):
                status_ia.text(f"⚖️ Procesando información con IA... {p}%")
                progress_ia.progress(p / 100)
                time.sleep(0.05)
            
            # --- DETECCIÓN DINÁMICA DE LA RUTA ---
            ruta_modelo = obtener_ruta_modelo(api_key)
            url_api = f"https://generativelanguage.googleapis.com/v1beta/{ruta_modelo}:generateContent?key={api_key}"
            
            prompt = f"""
            {fecha_referencia}.
            TAREA: Extracción de datos de prensa para informe técnico.
            
            ENTRADA DE DATOS:
            {noticias_raw}
            
            REGLAS DE FILTRADO:
            - Solo noticias desde el sábado hasta hoy lunes.
            - Prioridad: Economía, Impuestos, Estado, Gestión Pública.
            - Prioridad Geográfica: Cochabamba y Tarija.

            FORMATO:
            ** * TITULAR EN MAYÚSCULAS * **
            
            **MEDIO EN MAYÚSCULAS**
            
            Párrafo técnico informativo de 4 a 6 líneas.
            
            URL en minúsculas.
            """
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}
                ],
                "generationConfig": {"temperature": 0.0}
            }
            
            res = requests.post(url_api, json=payload)
            status_ia.empty()
            progress_ia.empty()
            
            if res.status_code == 200:
                try:
                    texto = res.json()['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(texto)
                except:
                    st.error("La IA bloqueó la respuesta por motivos de seguridad.")
            else:
                st.error(f"Error final {res.status_code}: {res.text}")
        else:
            st.error("No se capturaron suficientes noticias.")
