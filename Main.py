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

# --- PERSISTENCIA (FILTRO > 1 HORA) ---
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
    """Extrae la URL real de un enlace de resultado de Google"""
    parsed = urlparse(url_google)
    res = parse_qs(parsed.query).get('q')
    return res[0] if res else url_google

st.title(f"📰 MONITOREO ESTRATÉGICO: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_fuentes():
    fuentes = [
        # COCHABAMBA
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "ATB CBBA", "u": "https://www.atb.com.bo/seccion/cochabamba", "t": "TV", "r": "Cochabamba"},
        {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:tiktok.com+OR+site:x.com+impuestos+cochabamba+bolivia", "t": "Influencer", "r": "Cochabamba"},
        
        # SANTA CRUZ
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
        st.write(f"📡 Escaneando {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            vistos = 0
            
            for l in links:
                url_raw = l['href']
                # Limpiar si viene de Google
                url = limpiar_url_google(url_raw) if "google.com/url" in url_raw else url_raw
                
                if not url.startswith('http') or any(x in url for x in ['google.com/search', 'accounts.google']): continue
                if url in historial: continue
                
                texto = l.get_text().strip()
                if len(texto) < 20: continue
                
                try:
                    # Solo entramos a leer el contenido si es un link de noticia o post
                    rn = requests.get(url, headers=headers, timeout=7)
                    s_n = BeautifulSoup(rn.text, 'html.parser')
                    txt = " ".join([p.get_text().strip() for p in s_n.find_all('p', limit=3)])
                    
                    if len(txt) > 80 or f['t'] == "Influencer":
                        data_final += f"REGION: {f['r']} | TIPO: {f['t']} | MEDIO: {f['n']} | TITULAR: {texto} | TXT: {txt[:700]} | LINK: {url}\n\n"
                        guardar_historial(url)
                        vistos += 1
                except: continue
                if vistos >= 5: break
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE OFICIAL'):
        raw_data = procesar_fuentes()
        if len(raw_data) > 200:
            try:
                model = genai.GenerativeModel('models/gemini-flash-latest')
                prompt = f"""
                FECHA: {fecha_hoy_bonita}.
                REGLAS DE ORO:
                1. JERARQUÍA: 1. COCHABAMBA (1.1 Escritos, 1.2 TV, 1.3 Digital, 1.4 Influencers), 2. SANTA CRUZ (Igual sub-orden).
                2. PRIORIDAD TEMÁTICA: Noticias de IMPUESTOS siempre arriba de cada sub-sección.
                3. ENLACES: Solo usa el link directo proporcionado. NO generes links a Google.
                4. INFLUENCERS: Describe qué se ve en el post (video, foto, denuncia) y resume el mensaje.

                FORMATO:
                **TITULAR EN MAYÚSCULAS**
                **NOMBRE DEL MEDIO EN MAYÚSCULAS**
                Resumen (4-6 líneas).
                URL directo (ej: https://facebook.com/post/123)
                """
                res = model.generate_content([prompt, raw_data])
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {str(e)}")
