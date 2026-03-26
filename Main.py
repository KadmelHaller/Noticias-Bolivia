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

# --- CONFIGURACIÓN DE TIEMPO Y FILTROS ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')
HISTORIAL_FILE = "vistos_monitoreo.txt"

# Temas permitidos para el filtro de relevancia
TEMAS_OK = ["impuesto", "sin", "tribut", "factur", "fiscal", "econom", "gobiern", "arce", "dolar", "clausur", "aduana", "subsidio", "gasolina", "diesel", "presupuest"]

def gestionar_historial():
    if os.path.exists(HISTORIAL_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(HISTORIAL_FILE), zona_horaria)
        # Si la búsqueda se hace con menos de 1 hora de diferencia, NO restringe (muestra todo)
        if (ahora - mtime).total_seconds() < 3600: return set()
        with open(HISTORIAL_FILE, "r") as f: return set(f.read().splitlines())
    return set()

def guardar_historial(url):
    with open(HISTORIAL_FILE, "a") as f: f.write(url + "\n")

def limpiar_url_google(url_google):
    """Limpia redirecciones de Google para obtener el link directo a la red social"""
    parsed = urlparse(url_google)
    res = parse_qs(parsed.query).get('q')
    return res[0] if res else url_google

def es_relevante_y_actual(texto, url):
    txt = texto.lower()
    if any(old in txt for old in ["2021", "2022", "2023"]): return False
    return any(t in txt for t in TEMAS_OK) or any(t in url.lower() for t in TEMAS_OK)

st.title(f"📰 MONITOREO ESTRATÉGICO: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_fuentes():
    fuentes = [
        # --- COCHABAMBA ---
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "t": "Escrito", "r": "Cochabamba"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/seccion/cochabamba/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "ATB CBBA", "u": "https://www.atb.com.bo/seccion/cochabamba", "t": "TV", "r": "Cochabamba"},
        {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:tiktok.com+OR+site:instagram.com+OR+site:x.com+impuestos+cochabamba+2026", "t": "Influencer", "r": "Cochabamba"},
        
        # --- SANTA CRUZ ---
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/economia", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/category/economia/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL DÍA", "u": "https://www.eldia.com.bo/index.php?cat=357", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "UNITEL SCZ", "u": "https://unitel.bo/santa-cruz", "t": "TV", "r": "Santa Cruz"},
        {"n": "RRSS SCZ", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:tiktok.com+OR+site:instagram.com+OR+site:x.com+impuestos+santa+cruz+2026", "t": "Influencer", "r": "Santa Cruz"},

        # --- NACIONAL / OTROS ---
        {"n": "RED UNO", "u": "https://www.reduno.com.bo/noticias", "t": "TV", "r": "Nacional"},
        {"n": "BOLIVIA TV", "u": "https://www.boliviatv.bo/noticias", "t": "TV", "r": "Nacional"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/economia", "t": "Digital", "r": "Nacional"},
        {"n": "IN NOTICIAS", "u": "https://innoticiasbo.com/", "t": "Digital", "r": "Nacional"},
        {"n": "ENFOQUE NEWS", "u": "https://enfoquenews.com.bo/", "t": "Digital", "r": "Nacional"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}
    data_final = ""
    historial = gestionar_historial()
    pb = st.progress(0)
    
    for i, f in enumerate(fuentes):
        st.write(f"📡 Procesando {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            vistos = 0
            
            for l in links:
                url_raw = l['href']
                # Limpiar solo si es búsqueda de Google (RRSS)
                url = limpiar_url_google(url_raw) if "google.com/url" in url_raw else url_raw
                
                if not url.startswith('http') or "google.com/search" in url: continue
                if url in historial: continue
                
                # Filtro de profundidad para evitar portadas (solo para medios no RRSS)
                if f['t'] != "Influencer" and url.count('/') < 4: continue
                
                titulo = l.get_text().strip()
                if len(titulo) < 25: continue

                if es_relevante_y_actual(titulo, url):
                    try:
                        # ENTRAR A LA NOTA (Manteniendo la lógica anterior para Escritos/TV/Digital)
                        rn = requests.get(url, headers=headers, timeout=8)
                        s_n = BeautifulSoup(rn.text, 'html.parser')
                        parrafos = s_n.find_all('p', limit=5)
                        txt = " ".join([p.get_text().strip() for p in parrafos if len(p.get_text()) > 30])
                        
                        if len(txt) > 80 or f['t'] == "Influencer":
                            data_final += f"REGION: {f['r']} | TIPO: {f['t']} | MEDIO: {f['n']} | TITULAR: {titulo} | TXT: {txt[:850]} | LINK: {url}\n\n"
                            guardar_historial(url)
                            vistos += 1
                    except: continue
                if vistos >= 5: break
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE INTEGRAL'):
        with st.status("Ejecutando monitoreo...") as status:
            raw_data = procesar_fuentes()
            if len(raw_data) > 200:
                status.update(label="Analizando contenido con IA...", state="running")
                try:
                    model = genai.GenerativeModel('models/gemini-1.5-flash')
                    prompt = f"""
                    FECHA: {fecha_hoy_bonita}. PRIORIDAD: IMPUESTOS.
                    JERARQUÍA ESTRICTA:
                    1. COCHABAMBA: 1.1 Escritos, 1.2 TV, 1.3 Digital, 1.4 Influencers.
                    2. SANTA CRUZ: 1.1 Escritos, 1.2 TV, 1.3 Digital, 1.4 Influencers.
                    
                    INSTRUCCIONES:
                    - Dentro de cada sección, las noticias de IMPUESTOS/SIN van primero.
                    - Para Influencers (1.4), describe qué se muestra (video, denuncia, post) y el link directo.
                    - Formato: Títulos y Medios en MAYÚSCULAS. Resumen 4-6 líneas.
                    """
                    res = model.generate_content([prompt, raw_data])
                    status.update(label="Reporte finalizado", state="complete")
                    processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                    st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error en IA: {e}")
            else:
                st.warning("No se hallaron noticias que cumplan los filtros actuales.")
