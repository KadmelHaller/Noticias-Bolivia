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

# --- CONFIGURACIÓN ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')
HISTORIAL_FILE = "vistos_monitoreo.txt"

# Palabras clave con enfoque 100% Tributario y Económico
TEMAS_OK = ["impuesto", "sin", "tribut", "factur", "fiscal", "recaudaci", "clausur", "presupuesto", "aduana", "econom", "dolar", "banco", "gobierno"]

def gestionar_historial():
    if os.path.exists(HISTORIAL_FILE):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(HISTORIAL_FILE), zona_horaria)
            if (ahora - mtime).total_seconds() < 1800: return set() # 30 min para pruebas
            with open(HISTORIAL_FILE, "r") as f: return set(f.read().splitlines())
        except: return set()
    return set()

def guardar_historial(url):
    with open(HISTORIAL_FILE, "a") as f: f.write(url + "\n")

def es_relevante(texto, url):
    txt = (texto + url).lower()
    if any(old in txt for old in ["2021", "2022", "2023"]): return False
    return any(t in txt for t in TEMAS_OK)

st.title(f"📰 MONITOREO ENFOQUE IMPUESTOS: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_fuentes():
    # Lista de medios apuntando a Portadas o Secciones Críticas
    fuentes = [
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "t": "Escrito", "r": "Cochabamba"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "UNITEL", "u": "https://unitel.bo/", "t": "TV", "r": "Nacional"},
        {"n": "RED UNO", "u": "https://www.reduno.com.bo/", "t": "TV", "r": "Nacional"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/", "t": "Digital", "r": "Nacional"},
        {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=site:facebook.com+impuestos+cochabamba+hoy", "t": "Influencer", "r": "Cochabamba"},
        {"n": "RRSS SCZ", "u": "https://www.google.com/search?q=site:facebook.com+impuestos+santa+cruz+hoy", "t": "Influencer", "r": "Santa Cruz"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    data_final = ""
    historial = gestionar_historial()
    pb = st.progress(0)
    
    for i, f in enumerate(fuentes):
        st.write(f"🔎 Escaneando Portada: {f['n']}...")
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
                
                if url in historial or "google.com/search" in url: continue
                
                titulo = l.get_text().strip()
                if len(titulo) < 30: continue

                if es_relevante(titulo, url):
                    try:
                        # EXTRACCIÓN PROFUNDA DEL CUERPO
                        rn = requests.get(url, headers=headers, timeout=7)
                        s_n = BeautifulSoup(rn.text, 'html.parser')
                        # Buscamos párrafos significativos
                        parrafos = s_n.find_all('p', limit=6)
                        txt_cuerpo = " ".join([p.get_text().strip() for p in parrafos if len(p.get_text()) > 40])
                        
                        if len(txt_cuerpo) > 100 or f['t'] == "Influencer":
                            data_final += f"REGION: {f['r']} | MEDIO: {f['n']} | TITULAR: {titulo} | CONTENIDO: {txt_cuerpo[:900]} | LINK: {url}\n\n"
                            guardar_historial(url)
                            vistos += 1
                    except: continue
                if vistos >= 6: break # Capturamos más noticias por medio
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 EJECUTAR MONITOREO TRIBUTARIO'):
        with st.status("Buscando en portadas nacionales...") as status:
            raw_data = procesar_fuentes()
            if len(raw_data) > 200:
                status.update(label="Analizando impacto impositivo con IA...", state="running")
                try:
                    # Usamos el identificador de modelo más estable
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"""
                    FECHA: {fecha_hoy_bonita}. Eres un experto en política tributaria de Bolivia.
                    
                    TAREA: Genera un reporte basado EXCLUSIVAMENTE en noticias de IMPACTO ECONÓMICO E IMPUESTOS.
                    
                    ORDEN:
                    1. COCHABAMBA (Escritos, TV, Digital, RRSS).
                    2. SANTA CRUZ (Escritos, TV, Digital, RRSS).
                    
                    REQUISITOS:
                    - Si la noticia es de IMPUESTOS NACIONALES (SIN) o ADUANA, debe ir al principio de su sección.
                    - Formato: TITULAR EN MAYÚSCULAS, MEDIO EN MAYÚSCULAS, resumen de 5 líneas explicando el impacto para el ciudadano o empresa, y el LINK.
                    - Estilo: Formal, técnico y directo.
                    """
                    res = model.generate_content([prompt, raw_data])
                    status.update(label="Reporte Finalizado", state="complete")
                    processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                    st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error en Gemini: {str(e)}")
            else:
                st.warning("No se encontraron noticias con enfoque en impuestos en las portadas actuales. Reintentando con filtros generales...")
