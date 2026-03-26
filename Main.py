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

# Palabras clave estrictas para ahorrar cuota de API
TEMAS_OK = ["impuesto", "sin", "tribut", "factur", "fiscal", "econom", "gobiern", "arce", "dolar", "clausur", "aduana", "subsidio", "gasolina", "diesel", "presupuest"]

def gestionar_historial():
    if os.path.exists(HISTORIAL_FILE):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(HISTORIAL_FILE), zona_horaria)
            # Durante pruebas (<1h), no bloqueamos nada para que veas resultados
            if (ahora - mtime).total_seconds() < 3600: return set()
            with open(HISTORIAL_FILE, "r") as f: return set(f.read().splitlines())
        except: return set()
    return set()

def guardar_historial(url):
    with open(HISTORIAL_FILE, "a") as f: f.write(url + "\n")

def limpiar_url_google(url_google):
    if "google.com/url" in url_google:
        parsed = urlparse(url_google)
        res = parse_qs(parsed.query).get('q')
        return res[0] if res else url_google
    return url_google

def es_relevante_y_actual(texto, url):
    txt = texto.lower()
    if any(old in txt for old in ["2021", "2022", "2023"]): return False
    return any(t in txt for t in TEMAS_OK) or any(t in url.lower() for t in TEMAS_OK)

st.title(f"📰 MONITOREO ESTRATÉGICO: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_fuentes():
    fuentes = [
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "t": "Escrito", "r": "Cochabamba"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/seccion/cochabamba/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/economia", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "UNITEL", "u": "https://unitel.bo/noticias/economia", "t": "TV", "r": "Nacional"},
        {"n": "RED UNO", "u": "https://www.reduno.com.bo/noticias", "t": "TV", "r": "Nacional"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/economia", "t": "Digital", "r": "Nacional"},
        {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:x.com+impuestos+cochabamba", "t": "Influencer", "r": "Cochabamba"},
        {"n": "RRSS SCZ", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:x.com+impuestos+santa+cruz", "t": "Influencer", "r": "Santa Cruz"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    data_final = ""
    historial = gestionar_historial()
    pb = st.progress(0)
    
    for i, f in enumerate(fuentes):
        st.write(f"📡 Escaneando {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            vistos = 0
            
            for l in links:
                url_raw = l['href']
                url = limpiar_url_google(url_raw)
                if not url.startswith('http') or "google.com/search" in url: continue
                if url in historial: continue
                
                titulo = l.get_text().strip()
                if len(titulo) < 30: continue

                if es_relevante_y_actual(titulo, url):
                    try:
                        # LEER SOLO LO MÍNIMO (1-2 PÁRRAFOS) PARA AHORRAR TOKENS
                        rn = requests.get(url, headers=headers, timeout=6)
                        s_n = BeautifulSoup(rn.text, 'html.parser')
                        p = s_n.find('p')
                        txt = p.get_text().strip() if p else "Sin descripción extra."
                        
                        data_final += f"R: {f['r']} | T: {f['t']} | M: {f['n']} | TIT: {titulo} | TXT: {txt[:300]} | L: {url}\n\n"
                        guardar_historial(url)
                        vistos += 1
                    except: continue
                if vistos >= 3: break # Máximo 3 noticias por medio para no saturar la cuota
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE (MODO AHORRO CUOTA)'):
        with st.status("Procesando...") as status:
            raw_data = procesar_fuentes()
            if len(raw_data) > 100:
                try:
                    # Usando 1.5-flash que es más estable para cuotas gratuitas
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"Fecha: {fecha_hoy_bonita}. Prioridad: Impuestos. Jerarquía: 1.Cochabamba, 2.Santa Cruz (1.1 Escritos, 1.2 TV, 1.3 Dig, 1.4 RRSS). Formato: Titular Mayúsculas, Medio Mayúsculas, Resumen 4-6 líneas, URL."
                    res = model.generate_content([prompt, raw_data])
                    status.update(label="Reporte listo", state="complete")
                    processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                    st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("No hay noticias relevantes nuevas.")
