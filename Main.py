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

# --- CONFIGURACIÓN ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')
HISTORIAL_FILE = "vistos_monitoreo.txt"
TEMAS_OK = ["impuesto", "sin", "tributario", "factura", "economía", "gobierno", "arce", "dólar", "clausura", "fiscalización", "aduana", "subsidio", "gasolina", "diésel"]

def gestionar_historial():
    if os.path.exists(HISTORIAL_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(HISTORIAL_FILE), zona_horaria)
        if (ahora - mtime).total_seconds() < 3600: return set()
        with open(HISTORIAL_FILE, "r") as f: return set(f.read().splitlines())
    return set()

def guardar_historial(url):
    with open(HISTORIAL_FILE, "a") as f: f.write(url + "\n")

def es_relevante(texto):
    txt = texto.lower()
    if any(old in txt for old in ["2021", "2022", "2023"]): return False
    return any(t in txt for t in TEMAS_OK)

st.title(f"📰 MONITOREO ESTRATÉGICO: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Gemini API Key:", type="password")

def procesar_fuentes():
    fuentes = [
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "t": "Escrito", "r": "Cochabamba"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/seccion/cochabamba/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/economia", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/category/economia/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "LA ESTRELLA", "u": "https://www.laestrelladeloriente.com/category/nacional/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL DÍA", "u": "https://www.eldia.com.bo/index.php?cat=357", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "UNITEL", "u": "https://unitel.bo/noticias/economia", "t": "TV", "r": "Nacional"},
        {"n": "RED UNO", "u": "https://www.reduno.com.bo/noticias", "t": "TV", "r": "Nacional"},
        {"n": "ATB", "u": "https://www.atb.com.bo/seccion/economia", "t": "TV", "r": "Nacional"},
        {"n": "BOLIVIA TV", "u": "https://www.boliviatv.bo/noticias", "t": "TV", "r": "Nacional"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/economia", "t": "Digital", "r": "Nacional"},
        {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:x.com+impuestos+cochabamba+2026", "t": "Influencer", "r": "Cochabamba"},
        {"n": "RRSS SCZ", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:x.com+impuestos+santa+cruz+2026", "t": "Influencer", "r": "Santa Cruz"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    data_final = ""
    historial = gestionar_historial()
    pb = st.progress(0)
    
    for i, f in enumerate(fuentes):
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=6) # Timeout corto para evitar bloqueos
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)[:15] # Solo revisamos los primeros 15 links para mayor velocidad
            
            for l in links:
                url = l['href']
                if not url.startswith('http'): continue
                if url in historial or "google.com" in url: continue
                
                titulo = l.get_text().strip()
                if len(titulo) < 30: continue

                if es_relevante(titulo):
                    # Agregamos directamente para que la IA lo procese y evitar doble request
                    data_final += f"REGION: {f['r']} | TIPO: {f['t']} | MEDIO: {f['n']} | TITULAR: {titulo} | LINK: {url}\n\n"
                    guardar_historial(url)
                    if data_final.count('REGION:') > 20: break # Límite de seguridad
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE OFICIAL'):
        with st.spinner("Analizando fuentes en tiempo real..."):
            raw_data = procesar_fuentes()
            if len(raw_data) > 100:
                try:
                    model = genai.GenerativeModel('models/gemini-flash-latest')
                    prompt = f"FECHA: {fecha_hoy_bonita}. PRIORIDAD: IMPUESTOS. JERARQUÍA: 1. Cochabamba (1.1 Escritos, 1.2 TV, 1.3 Digital, 1.4 Influencer), 2. Santa Cruz (mismo orden). FORMATO: TÍTULO MAYÚSCULAS, MEDIO MAYÚSCULAS, resumen 4-6 líneas, URL. NOTA: Si no tienes el texto completo, infiere el impacto económico según el titular."
                    res = model.generate_content([prompt, raw_data])
                    processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                    st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error en IA: {e}")
            else:
                st.warning("No se encontraron noticias nuevas bajo los criterios de búsqueda.")
