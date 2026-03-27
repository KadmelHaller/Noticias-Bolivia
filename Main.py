import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
from urllib.parse import urlparse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitoreo Tributario", page_icon="🇧🇴", layout="wide")

zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')

# Filtros enfocados
TEMAS_OK = ["impuesto", "sin", "tribut", "factur", "fiscal", "recaudaci", "clausur", "presupuesto", "aduana", "econom", "dolar", "banco", "gobierno"]

def es_relevante(texto, url):
    txt = (texto + url).lower()
    if any(old in txt for old in ["2021", "2022", "2023"]): return False
    return any(t in txt for t in TEMAS_OK)

st.title(f"📰 MONITOREO TRIBUTARIO: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_fuentes():
    fuentes = [
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "t": "Escrito", "r": "Cochabamba"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "UNITEL", "u": "https://unitel.bo/noticias/economia", "t": "TV", "r": "Nacional"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/economia", "t": "Digital", "r": "Nacional"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}
    data_final = ""
    pb = st.progress(0)
    
    for i, f in enumerate(fuentes):
        st.write(f"📡 Escaneando: {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            vistos = 0
            
            for l in links:
                url_raw = l['href']
                url = url_raw if url_raw.startswith('http') else urlparse(f['u']).scheme + "://" + urlparse(f['u']).netloc + "/" + url_raw.lstrip('/')
                
                if "google.com" in url or len(url) < 35: continue
                
                titulo = l.get_text().strip()
                if len(titulo) < 30: continue

                if es_relevante(titulo, url):
                    try:
                        rn = requests.get(url, headers=headers, timeout=5)
                        s_n = BeautifulSoup(rn.text, 'html.parser')
                        parrafos = [p.get_text().strip() for p in s_n.find_all('p') if len(p.get_text()) > 60]
                        txt_cuerpo = " ".join(parrafos[:2]) 
                        
                        if len(txt_cuerpo) > 50:
                            data_final += f"REGION: {f['r']} | MEDIO: {f['n']} | TITULAR: {titulo} | TXT: {txt_cuerpo[:400]} | LINK: {url}\n\n"
                            vistos += 1
                    except: continue
                if vistos >= 4: break 
        except: continue
    return data_final

if api_key:
    # --- CORRECCIÓN DEFINITIVA DE IA ---
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"Error de configuración: {e}")

    if st.button('🚀 GENERAR REPORTE UNIFICADO'):
        with st.status("Procesando información...") as status:
            raw_data = procesar_fuentes()
            
            if len(raw_data) > 50:
                status.update(label="Redactando reporte final...", state="running")
                try:
                    # Usamos 'gemini-1.5-flash-latest' que es el alias más estable para evitar el 404
                    model = genai.GenerativeModel(model_name='gemini-1.5-flash-latest')
                    
                    prompt = f"""
                    FECHA: {fecha_hoy_bonita}. Eres un analista de prensa.
                    REGLA DE ORO: Cambia 'Impuestos Municipales', 'Impuestos Nacionales' o cualquier variante a la palabra única 'IMPUESTOS'.
                    
                    ESTRUCTURA:
                    1. COCHABAMBA
                    2. SANTA CRUZ
                    
                    FORMATO:
                    **TITULAR EN MAYÚSCULAS**
                    **MEDIO EN MAYÚSCULAS**
                    Resumen técnico de 4 líneas enfocado en IMPUESTOS.
                    URL
                    """
                    
                    res = model.generate_content(prompt + "\n\nDATOS:\n" + raw_data)
                    
                    status.update(label="Reporte Completado", state="complete")
                    
                    # Limpieza y visualización
                    processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                    st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                except Exception as e:
                    # Si falla el 'latest', intentamos con la ruta de sistema
                    try:
                        model = genai.GenerativeModel(model_name='models/gemini-1.5-flash')
                        res = model.generate_content(prompt + "\n\nDATOS:\n" + raw_data)
                        status.update(label="Reporte Completado", state="complete")
                        processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                        st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                    except Exception as e2:
                        st.error(f"Error técnico persistente: {e2}")
            else:
                st.warning("No se detectaron noticias nuevas sobre impuestos.")
