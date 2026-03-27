import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
from urllib.parse import urlparse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor Estratégico Bolivia", page_icon="🇧🇴", layout="wide")

zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# Prioridades: 1. Impuestos, 2. Gobierno, 3. Economía
KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "gobierno", "arce", "ministro", "estado", "economia", "dolar", "banco", "crisis"]

# --- ESTADO DE SESIÓN PARA PERSISTENCIA ---
if 'reporte_medios' not in st.session_state:
    st.session_state.reporte_medios = ""
if 'reporte_rrss' not in st.session_state:
    st.session_state.reporte_rrss = ""

st.title(f"🔍 MONITOR ESTRATÉGICO BOLIVIA: {fecha_hoy}")
st.markdown("### Cobertura: Cochabamba, Santa Cruz y Nacional")

api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

def scraping_avanzado(lista_fuentes):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    acumulado = ""
    pb = st.progress(0)
    for i, f in enumerate(lista_fuentes):
        st.write(f"📡 Escaneando: {f['n']}...")
        pb.progress((i + 1) / len(lista_fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            for link in links:
                tit = link.get_text().strip()
                url = link['href']
                if not url.startswith('http'):
                    base = urlparse(f['u']).scheme + "://" + urlparse(f['u']).netloc
                    url = base + "/" + url.lstrip('/')
                
                if len(tit) > 25 and any(k in (tit + url).lower() for k in KEYWORDS):
                    acumulado += f"REGION: {f['r']} | MEDIO: {f['n']} | TITULO: {tit} | LINK: {url}\n\n"
        except: continue
    return acumulado

def procesar_ia(datos, contexto):
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_final = next((m for m in modelos if 'flash' in m), modelos[0])
        model = genai.GenerativeModel(modelo_final)
        
        prompt = f"""
        FECHA: {fecha_hoy}. FUENTES: {contexto}.
        PRIORIDAD: 1. IMPUESTOS (unificar términos), 2. GOBIERNO, 3. ECONOMÍA.
        ESTRUCTURA:
        1. COCHABAMBA (Opinión, Los Tiempos, La Voz de Tarija, Urgente, Innoticias, EnfoqueNews, TV).
        2. SANTA CRUZ (El Deber, El Mundo, TV).
        REQUISITO: TITULAR (MAYUS), MEDIO (MAYUS), Resumen 5 líneas, LINK.
        """
        res = model.generate_content(prompt + "\n\nDATOS:\n" + datos)
        return res.text
    except Exception as e:
        return f"Error en IA: {str(e)}"

# --- LÓGICA DE BOTONES ---

if api_key:
    genai.configure(api_key=api_key)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button('🚀 FASE 1: MEDIOS ESCRITOS, TV Y DIGITAL'):
            fuentes_tradicionales = [
                # COCHABAMBA
                {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba"},
                {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "r": "Cochabamba"},
                {"n": "LA VOZ DE TARIJA", "u": "https://lavozdetarija.com/", "r": "Cochabamba/Nacional"},
                {"n": "URGENTE.BO", "u": "https://www.urgente.bo/", "r": "Cochabamba/Nacional"},
                {"n": "INNOTICIAS", "u": "https://innoticiasbo.com/", "r": "Cochabamba"},
                {"n": "ENFOQUE NEWS", "u": "https://enfoquenews.com.bo/", "r": "Cochabamba"},
                # SANTA CRUZ
                {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "r": "Santa Cruz"},
                {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "r": "Santa Cruz"},
                # TV (NACIONAL/AMBAS CIUDADES)
                {"n": "UNITEL", "u": "https://unitel.bo/", "r": "Nacional"},
                {"n": "RED UNO", "u": "https://www.reduno.com.bo/", "r": "Nacional"},
                {"n": "BOLIVISIÓN", "u": "https://www.redbolivision.tv.bo/", "r": "Nacional"},
                {"n": "BOLIVIA TV", "u": "https://www.boliviatv.bo/", "r": "Nacional"},
                {"n": "PAT", "u": "https://www.pat.bo/", "r": "Nacional"},
                {"n": "RTP", "u": "https://www.rtpbolivia.com.bo/", "r": "Nacional"},
                {"n": "ATB", "u": "https://www.atb.com.bo/", "r": "Nacional"}
            ]
            datos_m = scraping_avanzado(fuentes_tradicionales)
            if datos_m:
                st.session_state.reporte_medios = procesar_ia(datos_m, "Medios Tradicionales y TV")
            else:
                st.warning("No se hallaron noticias relevantes en esta fase.")

    with col2:
        if st.button('📱 FASE 2: RELEVAMIENTO REDES SOCIALES'):
            fuentes_rrss = [
                {"n": "FB/X CBBA", "u": "https://www.google.com/search?q=impuestos+Cochabamba+site:facebook.com+OR+site:x.com", "r": "Cochabamba"},
                {"n": "IG/TK CBBA", "u": "https://www.google.com/search?q=impuestos+Cochabamba+site:instagram.com+OR+site:tiktok.com", "r": "Cochabamba"},
                {"n": "FB/X SCZ", "u": "https://www.google.com/search?q=impuestos+Santa+Cruz+site:facebook.com+OR+site:x.com", "r": "Santa Cruz"},
                {"n": "IG/TK SCZ", "u": "https://www.google.com/search?q=impuestos+Santa+Cruz+site:instagram.com+OR+site:tiktok.com", "r": "Santa Cruz"}
            ]
            datos_r = scraping_avanzado(fuentes_rrss)
            if datos_r:
                st.session_state.reporte_rrss = procesar_ia(datos_r, "Redes Sociales (FB, X, IG, TK)")
            else:
                st.warning("No se hallaron menciones relevantes en Redes Sociales.")

    # --- DESPLIEGUE DE RESULTADOS ---
    
    if st.session_state.reporte_medios:
        st.markdown("### 📰 REPORTE: PRENSA ESCRITA Y TELEVISIÓN")
        st.markdown(f'<div style="background: white; color: black; padding: 25px; border: 1px solid #ccc; font-family: serif;">{st.session_state.reporte_medios.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

    if st.session_state.reporte_rrss:
        st.markdown("---")
        st.markdown("### 📱 REPORTE: REDES SOCIALES")
        st.markdown(f'<div style="background: #f9f9f9; color: black; padding: 25px; border: 1px solid #00acee; font-family: serif;">{st.session_state.reporte_rrss.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
else:
    st.info("Ingresa tu API Key en la barra lateral para activar el monitoreo.")
