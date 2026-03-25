import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import os
from urllib.parse import urlparse, parse_qs

st.set_page_config(page_title="Monitoreo Bolivia Pro", page_icon="🇧🇴", layout="wide")

# --- FILTRO TÉCNICO DE TEMAS ---
TEMAS_PERMITIDOS = ["impuesto", "sin", "tributario", "factura", "economía", "gobierno", "arce", "alcaldía", "presupuesto", "dólar", "clausura", "fiscalización"]

# --- PERSISTENCIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')
HISTORIAL_FILE = "vistos_monitoreo.txt"

def gestionar_historial():
    if os.path.exists(HISTORIAL_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(HISTORIAL_FILE), zona_horaria)
        if (ahora - mtime).total_seconds() < 3600: return set()
        with open(HISTORIAL_FILE, "r") as f: return set(f.read().splitlines())
    return set()

def guardar_historial(url):
    with open(HISTORIAL_FILE, "a") as f: f.write(url + "\n")

def limpiar_url_google(url_google):
    parsed = urlparse(url_google)
    res = parse_qs(parsed.query).get('q')
    return res[0] if res else url_google

st.title(f"📰 MONITOREO ESTRATÉGICO: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def es_contenido_relevante(texto):
    """Verifica si el texto trata sobre los temas permitidos y no es antiguo"""
    texto_min = texto.lower()
    # Filtro de fecha para evitar noticias de 2021, 2022, 2023
    if any(año in texto_min for año in ["2021", "2022", "2023"]): return False
    # Filtro de palabras clave
    return any(tema in texto_min for tema in TEMAS_PERMITIDOS)

def procesar_fuentes():
    fuentes = [
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "ATB CBBA", "u": "https://www.atb.com.bo/seccion/cochabamba", "t": "TV", "r": "Cochabamba"},
        {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:tiktok.com+OR+site:x.com+impuestos+cochabamba+bolivia", "t": "Influencer", "r": "Cochabamba"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL DÍA", "u": "https://www.eldia.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "UNITEL SCZ", "u": "https://unitel.bo/santa-cruz", "t": "TV", "r": "Santa Cruz"},
        {"n": "RRSS SCZ", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:tiktok.com+OR+site:x.com+impuestos+santa+cruz+bolivia", "t": "Influencer", "r": "Santa Cruz"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}
    data_final = ""
    historial = gestionar_historial()
    pb = st.progress(0)
    
    for i, f in enumerate(fuentes):
        st.write(f"📡 Filtrando {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            vistos = 0
            
            for l in links:
                url_raw = l['href']
                url = limpiar_url_google(url_raw) if "google.com/url" in url_raw else url_raw
                if not url.startswith('http') or "google.com" in url: continue
                
                # EVITAR URLS GENÉRICAS DE SECCIÓN (Deben tener más de 3 niveles de profundidad)
                if url.rstrip('/').count('/') < 4 and f['t'] != "Influencer": continue
                
                if url in historial: continue
                
                titulo = l.get_text().strip()
                if len(titulo) < 20: continue
                
                # PRIMER FILTRO: ¿El título es relevante?
                if es_contenido_relevante(titulo):
                    try:
                        rn = requests.get(url, headers=headers, timeout=7)
                        s_n = BeautifulSoup(rn.text, 'html.parser')
                        # Limpiar texto de la nota
                        txt = " ".join([p.get_text().strip() for p in s_n.find_all('p', limit=4)])
                        
                        # SEGUNDO FILTRO: ¿El cuerpo de la noticia es relevante y actual?
                        if es_contenido_relevante(txt):
                            data_final += f"REGION: {f['r']} | TIPO: {f['t']} | MEDIO: {f['n']} | TITULAR: {titulo} | TXT: {txt[:800]} | LINK: {url}\n\n"
                            guardar_historial(url)
                            vistos += 1
                    except: continue
                
                if vistos >= 5: break
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE FILTRADO'):
        raw_data = procesar_fuentes()
        if len(raw_data) > 100:
            try:
                model = genai.GenerativeModel('models/gemini-flash-latest')
                prompt = f"""
                FECHA ACTUAL: {fecha_hoy_bonita}.
                
                SOLO INCLUYE NOTICIAS SOBRE: IMPUESTOS (PRIORIDAD), ECONOMÍA O GOBIERNO BOLIVIANO.
                ELIMINA: Noticias de salud, medio ambiente, deportes o de años pasados (2021-2023).
                
                JERARQUÍA:
                1. COCHABAMBA (1.1 Escritos, 1.2 TV, 1.3 Digital, 1.4 Influencers)
                2. SANTA CRUZ (Igual sub-orden)

                ESTRUCTURA:
                **TITULAR EN MAYÚSCULAS**
                **NOMBRE DEL MEDIO EN MAYÚSCULAS**
                Resumen técnico (4-6 líneas).
                URL directo (asegúrate de que sea la nota específica, no la sección).
                """
                res = model.generate_content([prompt, raw_data])
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.warning("No se encontraron noticias recientes y relevantes sobre Impuestos/Economía en este momento.")
