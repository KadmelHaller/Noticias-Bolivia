import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import os
from urllib.parse import urlparse

st.set_page_config(page_title="Monitoreo Bolivia Pro", page_icon="🇧🇴", layout="wide")

# --- CONFIGURACIÓN DE TIEMPO Y FILTROS ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')

# Enfoque estricto en IMPUESTOS y ECONOMÍA
TEMAS_OK = ["impuesto", "sin", "tribut", "factur", "fiscal", "recaudaci", "clausur", "presupuesto", "aduana", "econom", "dolar", "banco", "gobierno"]

def es_relevante(texto, url):
    txt = (texto + url).lower()
    if any(old in txt for old in ["2021", "2022", "2023"]): return False
    return any(t in txt for t in TEMAS_OK)

st.title(f"📰 MONITOREO ENFOQUE IMPUESTOS: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_fuentes():
    fuentes = [
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "t": "Escrito", "r": "Cochabamba"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "UNITEL", "u": "https://unitel.bo/", "t": "TV", "r": "Nacional"},
        {"n": "RED UNO", "u": "https://www.reduno.com.bo/", "t": "TV", "r": "Nacional"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/", "t": "Digital", "r": "Nacional"},
        {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=site:facebook.com+impuestos+cochabamba", "t": "Influencer", "r": "Cochabamba"},
        {"n": "RRSS SCZ", "u": "https://www.google.com/search?q=site:facebook.com+impuestos+santa+cruz", "t": "Influencer", "r": "Santa Cruz"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    data_final = ""
    pb = st.progress(0)
    
    for i, f in enumerate(fuentes):
        st.write(f"📡 Escaneando: {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            vistos = 0
            
            for l in links:
                url_raw = l['href']
                if not url_raw.startswith('http'):
                    base = urlparse(f['u']).scheme + "://" + urlparse(f['u']).netloc
                    url = base + "/" + url_raw.lstrip('/')
                else:
                    url = url_raw
                
                if "google.com" in url: continue
                
                titulo = l.get_text().strip()
                if len(titulo) < 30: continue

                if es_relevante(titulo, url):
                    try:
                        # EXTRACCIÓN PROFUNDA (Entrar a la nota)
                        rn = requests.get(url, headers=headers, timeout=7)
                        s_n = BeautifulSoup(rn.text, 'html.parser')
                        parrafos = s_n.find_all('p', limit=6)
                        txt_cuerpo = " ".join([p.get_text().strip() for p in parrafos if len(p.get_text()) > 40])
                        
                        if len(txt_cuerpo) > 80 or f['t'] == "Influencer":
                            data_final += f"REGION: {f['r']} | MEDIO: {f['n']} | TITULAR: {titulo} | CONTENIDO: {txt_cuerpo[:900]} | LINK: {url}\n\n"
                            vistos += 1
                    except: continue
                if vistos >= 6: break 
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 EJECUTAR MONITOREO TRIBUTARIO'):
        with st.status("Escaneando portadas y redes...") as status:
            raw_data = procesar_fuentes()
            if len(raw_data) > 100:
                status.update(label="Generando reporte final...", state="running")
                try:
                    # MODELO CONFIGURADO PARA EVITAR ERROR 404
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"""
                    FECHA: {fecha_hoy_bonita}. Eres un experto en política tributaria boliviana.
                    Organiza este reporte: 1.Cochabamba, 2.Santa Cruz.
                    Prioridad: IMPUESTOS, SIN, RECAUDACIÓN.
                    Formato: TITULAR (MAYUS), MEDIO (MAYUS), resumen técnico 5 líneas, URL.
                    """
                    res = model.generate_content([prompt, raw_data])
                    status.update(label="Completado", state="complete")
                    processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                    st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error en IA: {e}")
            else:
                st.warning("No se hallaron noticias con los criterios actuales.")
