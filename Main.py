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

if 'reporte_medios' not in st.session_state:
    st.session_state.reporte_medios = ""
if 'reporte_rrss' not in st.session_state:
    st.session_state.reporte_rrss = ""

st.title(f"🔍 MONITOR ESTRATÉGICO BOLIVIA: {fecha_hoy}")

api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

def scraping_limpio(fuentes):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    datos = ""
    pb = st.progress(0)
    for i, f in enumerate(fuentes):
        st.write(f"📡 Escaneando: {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                tit = link.get_text().strip()
                url = link['href']
                if not url.startswith('http'):
                    base = urlparse(f['u']).scheme + "://" + urlparse(f['u']).netloc
                    url = base + "/" + url.lstrip('/')
                
                if len(tit) > 25 and any(k in (tit + url).lower() for k in KEYWORDS):
                    datos += f"ORIGEN_FUENTE: {f['n']} | CIUDAD_MEDIO: {f['r']} | INFO: {tit} | LINK: {url}\n\n"
        except: continue
    return datos

def procesar_reporte(datos_raw, es_rrss=False):
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_final = next((m for m in modelos if 'flash' in m), modelos[0])
        model = genai.GenerativeModel(modelo_final)
        
        tipo_fuente = "REDES SOCIALES" if es_rrss else "PRENSA Y TV"
        
        prompt = f"""
        FECHA: {fecha_hoy}. FUENTES: {tipo_fuente}.
        PRIORIDAD TEMÁTICA: 1. IMPUESTOS (unificar), 2. GOBIERNO, 3. ECONOMÍA.

        ESTRUCTURA OBLIGATORIA:
        1. COCHABAMBA (Incluir aquí periódicos de Cbba y noticias de TV que hablen de Cbba).
        2. SANTA CRUZ (Incluir aquí periódicos de SCZ y noticias de TV que hablen de SCZ).

        FORMATO DE SALIDA (ESTRICTO):
        **TITULAR EN MAYÚSCULAS** - **NOMBRE DEL MEDIO**
        Texto del resumen de 5 líneas sin etiquetas previas, analizando el impacto.
        Enlace directo aquí.

        PROHIBICIONES: No uses palabras como 'Resumen:', 'URL:', 'Título:' o 'Link:'. La información debe ser directa.
        """
        res = model.generate_content(prompt + "\n\nDATOS RECOPILADOS:\n" + datos_raw)
        return res.text
    except Exception as e:
        return f"Error en procesamiento: {str(e)}"

# --- ACCIONES ---

if api_key:
    genai.configure(api_key=api_key)
    c1, c2 = st.columns(2)
    
    with c1:
        if st.button('🚀 FASE 1: PRENSA Y TV'):
            medios = [
                # CBBA
                {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba"},
                {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "r": "Cochabamba"},
                {"n": "LA VOZ DE TARIJA", "u": "https://lavozdetarija.com/", "r": "Nacional"},
                {"n": "URGENTE.BO", "u": "https://www.urgente.bo/", "r": "Nacional"},
                {"n": "INNOTICIAS", "u": "https://innoticiasbo.com/", "r": "Cochabamba"},
                {"n": "ENFOQUE NEWS", "u": "https://enfoquenews.com.bo/", "r": "Cochabamba"},
                # SCZ
                {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "r": "Santa Cruz"},
                {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "r": "Santa Cruz"},
                # TV
                {"n": "UNITEL", "u": "https://unitel.bo/", "r": "Nacional"},
                {"n": "RED UNO", "u": "https://www.reduno.com.bo/", "r": "Nacional"},
                {"n": "BOLIVISIÓN", "u": "https://www.redbolivision.tv.bo/", "r": "Nacional"},
                {"n": "BOLIVIA TV", "u": "https://www.boliviatv.bo/", "r": "Nacional"},
                {"n": "PAT", "u": "https://www.pat.bo/", "r": "Nacional"},
                {"n": "RTP", "u": "https://www.rtpbolivia.com.bo/", "r": "Nacional"},
                {"n": "ATB", "u": "https://www.atb.com.bo/", "r": "Nacional"}
            ]
            datos_brutos = scraping_limpio(medios)
            if datos_brutos:
                st.session_state.reporte_medios = procesar_reporte(datos_brutos)

    with c2:
        if st.button('📱 FASE 2: REDES SOCIALES'):
            rrss_queries = [
                {"n": "FB/X CBBA", "u": "https://www.google.com/search?q=impuestos+Cochabamba+site:facebook.com+OR+site:x.com", "r": "Cochabamba"},
                {"n": "IG/TK CBBA", "u": "https://www.google.com/search?q=impuestos+Cochabamba+site:instagram.com+OR+site:tiktok.com", "r": "Cochabamba"},
                {"n": "FB/X SCZ", "u": "https://www.google.com/search?q=impuestos+Santa+Cruz+site:facebook.com+OR+site:x.com", "r": "Santa Cruz"},
                {"n": "IG/TK SCZ", "u": "https://www.google.com/search?q=impuestos+Santa+Cruz+site:instagram.com+OR+site:tiktok.com", "r": "Santa Cruz"}
            ]
            datos_rrss = scraping_limpio(rrss_queries)
            if datos_rrss:
                st.session_state.reporte_rrss = procesar_reporte(datos_rrss, es_rrss=True)

    # --- SALIDA ---
    if st.session_state.reporte_medios:
        st.subheader("📰 REPORTE DE PRENSA Y TELEVISIÓN")
        # El reemplazo de asteriscos por <b> ayuda a que Streamlit renderice negritas correctamente
        res_html = st.session_state.reporte_medios.replace("\n", "<br>")
        st.markdown(f'<div style="background: white; color: black; padding: 25px; border: 1px solid #ccc; font-family: serif; text-align: justify;">{res_html}</div>', unsafe_allow_html=True)

    if st.session_state.reporte_rrss:
        st.markdown("---")
        st.subheader("📱 REPORTE DE REDES SOCIALES")
        res_rrss_html = st.session_state.reporte_rrss.replace("\n", "<br>")
        st.markdown(f'<div style="background: #fdfdfd; color: black; padding: 25px; border: 1px solid #00acee; font-family: serif; text-align: justify;">{res_rrss_html}</div>', unsafe_allow_html=True)

else:
    st.warning("Configura tu API Key en el panel lateral.")
