import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
from urllib.parse import urlparse

st.set_page_config(page_title="Monitoreo Tributario Pro", page_icon="🇧🇴", layout="wide")

# --- CONFIGURACIÓN DE TIEMPO ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')

# --- FILTROS DE BÚSQUEDA (DIRECTO A IMPUESTOS) ---
# Se eliminaron términos específicos para priorizar la búsqueda general de Impuestos
TEMAS_OK = ["impuestos", "sin", "tributaria", "facturación", "aduana", "economía", "fiscal", "recaudación"]

def es_relevante(texto, url):
    txt = (texto + url).lower()
    # Excluimos años pasados para asegurar actualidad
    if any(old in txt for old in ["2021", "2022", "2023"]): return False
    return any(t in txt for t in TEMAS_OK)

st.title(f"📰 MONITOREO DE IMPUESTOS: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_fuentes():
    fuentes = [
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "t": "Escrito", "r": "Cochabamba"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "UNITEL", "u": "https://unitel.bo/noticias/economia", "t": "TV", "r": "Nacional"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/", "t": "Digital", "r": "Nacional"},
        {"n": "RRSS", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:x.com+impuestos+bolivia+2026", "t": "Influencer", "r": "Nacional"}
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
                
                if "google.com/search" in url or len(url) < 30: continue
                
                titulo = l.get_text().strip()
                if len(titulo) < 30: continue

                if es_relevante(titulo, url):
                    try:
                        # EXTRACCIÓN PROFUNDA (Solo para medios, no para RRSS)
                        if f['t'] != "Influencer":
                            rn = requests.get(url, headers=headers, timeout=5)
                            s_n = BeautifulSoup(rn.text, 'html.parser')
                            # Extraemos párrafos con contenido real
                            parrafos = [p.get_text().strip() for p in s_n.find_all('p') if len(p.get_text()) > 50]
                            txt_cuerpo = " ".join(parrafos[:3]) # Limitamos a 3 párrafos para no colgar la IA
                        else:
                            txt_cuerpo = "Publicación en Redes Sociales sobre impuestos."
                        
                        if len(txt_cuerpo) > 40:
                            data_final += f"REGION: {f['r']} | MEDIO: {f['n']} | TITULAR: {titulo} | RESUMEN_RAW: {txt_cuerpo[:600]} | LINK: {url}\n\n"
                            vistos += 1
                    except: continue
                if vistos >= 5: break 
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE INTEGRAL'):
        with st.status("Procesando información...") as status:
            raw_data = procesar_fuentes()
            if len(raw_data) > 100:
                status.update(label="Redactando reporte final...", state="running")
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"""
                    FECHA: {fecha_hoy_bonita}. Eres un analista de prensa experto.
                    Tu objetivo es reportar noticias sobre IMPUESTOS en Bolivia.
                    
                    ORGANIZACIÓN:
                    1. COCHABAMBA (Escritos, TV, Digital, RRSS).
                    2. SANTA CRUZ (Escritos, TV, Digital, RRSS).
                    
                    INSTRUCCIONES:
                    - Usa el término general 'IMPUESTOS' para categorizar la información.
                    - Formato: TITULAR (MAYÚSCULAS), MEDIO (MAYÚSCULAS), resumen ejecutivo de 4-5 líneas y el LINK.
                    - Si la noticia es de Redes Sociales, indica el tipo de tendencia.
                    """
                    res = model.generate_content([prompt, raw_data])
                    status.update(label="Reporte Completado", state="complete")
                    processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                    st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error en el análisis final: {e}")
            else:
                st.warning("No se encontraron noticias recientes sobre Impuestos en las portadas revisadas.")
