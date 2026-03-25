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

# --- CONFIGURACIÓN DE TIEMPO ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')
HISTORIAL_FILE = "vistos_monitoreo.txt"

# --- PALABRAS CLAVE AMPLIADAS PARA NO PERDER NOTICIAS ---
TEMAS_OK = ["impuesto", "sin", "tributario", "factura", "economía", "gobierno", "arce", "dólar", "clausura", "fiscalización", "presupuesto", "aduana", "subsidio", "combustible", "gasolina"]

def gestionar_historial():
    if os.path.exists(HISTORIAL_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(HISTORIAL_FILE), zona_horaria)
        if (ahora - mtime).total_seconds() < 3600: return set()
        with open(HISTORIAL_FILE, "r") as f: return set(f.read().splitlines())
    return set()

def guardar_historial(url):
    with open(HISTORIAL_FILE, "a") as f: f.write(url + "\n")

def es_relevante_y_actual(texto, url):
    txt = texto.lower()
    # Bloqueo estricto de años pasados
    if any(old in txt for old in ["2021", "2022", "2023"]): return False
    # Verificación de temas
    return any(t in txt for t in TEMAS_OK) or any(t in url.lower() for t in TEMAS_OK)

st.title(f"📰 MONITOREO ESTRATÉGICO: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_fuentes():
    # Ajustamos las URLs a las secciones donde REALMENTE están las noticias de economía/impuestos
    fuentes = [
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/seccion/cochabamba/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/actualidad/economia", "t": "Escrito", "r": "Cochabamba"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/economia", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/category/economia/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "LA ESTRELLA", "u": "https://www.laestrelladeloriente.com/category/nacional/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "UNITEL", "u": "https://unitel.bo/noticias/economia", "t": "TV", "r": "Nacional"},
        {"n": "ATB", "u": "https://www.atb.com.bo/seccion/economia", "t": "TV", "r": "Nacional"},
        {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:x.com+impuestos+cochabamba+2025+2026", "t": "Influencer", "r": "Cochabamba"},
        {"n": "RRSS SCZ", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:x.com+impuestos+santa+cruz+2025+2026", "t": "Influencer", "r": "Santa Cruz"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}
    data_final = ""
    historial = gestionar_historial()
    pb = st.progress(0)
    
    for i, f in enumerate(fuentes):
        st.write(f"📡 Buscando en {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            # Buscamos enlaces que parezcan notas (con cierta longitud o estructura)
            links = soup.find_all('a', href=True)
            vistos = 0
            
            for l in links:
                url = l['href']
                if not url.startswith('http'): 
                    base = urlparse(f['u']).scheme + "://" + urlparse(f['u']).netloc
                    url = base + "/" + url.lstrip('/')
                
                if url in historial or "google.com" in url: continue
                # Filtro de profundidad para evitar portadas de sección
                if url.count('/') < 4 and f['t'] != "Influencer": continue
                
                titulo = l.get_text().strip()
                if len(titulo) < 25: continue

                # Verificamos relevancia básica en el título antes de entrar
                if es_relevante_y_actual(titulo, url):
                    try:
                        rn = requests.get(url, headers=headers, timeout=8)
                        s_n = BeautifulSoup(rn.text, 'html.parser')
                        # Capturamos el texto principal de la noticia
                        parrafos = s_n.find_all('p', limit=5)
                        txt = " ".join([p.get_text().strip() for p in parrafos if len(p.get_text()) > 30])
                        
                        if len(txt) > 100 and not any(año in txt for año in ["2021", "2022", "2023"]):
                            data_final += f"REGION: {f['r']} | TIPO: {f['t']} | MEDIO: {f['n']} | TITULAR: {titulo} | TXT: {txt[:800]} | LINK: {url}\n\n"
                            guardar_historial(url)
                            vistos += 1
                    except: continue
                if vistos >= 4: break
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
                FECHA: {fecha_hoy_bonita}. Eres un analista de inteligencia económica.
                REGLA: PRIORIZA IMPUESTOS sobre cualquier otro tema.
                
                JERARQUÍA:
                1. COCHABAMBA (1.1 Escritos, 1.2 TV, 1.3 Digital, 1.4 Influencers)
                2. SANTA CRUZ (1.1 Escritos, 1.2 TV, 1.3 Digital, 1.4 Influencers)

                ESTRUCTURA:
                **TITULAR EN MAYÚSCULAS**
                **NOMBRE DEL MEDIO EN MAYÚSCULAS**
                Resumen de 4 a 6 líneas detallando el impacto fiscal o económico.
                URL directo
                """
                res = model.generate_content([prompt, raw_data])
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error en Gemini: {str(e)}")
        else:
            st.warning("No se hallaron noticias frescas de Impuestos/Economía. Verifica que los temas estén en la agenda de hoy.")
