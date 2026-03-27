import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
from urllib.parse import urlparse

st.set_page_config(page_title="Monitor Estratégico Bolivia", page_icon="🇧🇴", layout="wide")

zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# Palabras clave ultra-ampliadas
KEYWORDS = [
    "impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "muni",
    "gobierno", "arce", "ministro", "estado", "presidencia", "alcalde", "gestión",
    "economia", "dolar", "banco", "crisis", "subvención", "combustible", "escasez"
]

if 'reporte_medios' not in st.session_state: st.session_state.reporte_medios = ""
if 'reporte_rrss' not in st.session_state: st.session_state.reporte_rrss = ""

st.title(f"🔍 MONITOR ESTRATÉGICO TOTAL: {fecha_hoy}")
api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

def scraping_agresivo(fuentes):
    # Cabeceras completas para saltar bloqueos
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
        'Referer': 'https://www.google.com/'
    }
    datos = ""
    pb = st.progress(0)
    for i, f in enumerate(fuentes):
        st.write(f"📡 Extrayendo datos de: {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Buscamos en enlaces Y en encabezados (algunos medios no ponen el texto dentro del <a>)
            elementos = soup.find_all(['a', 'h1', 'h2', 'h3'])
            vistos = set() # Evitar duplicados del mismo medio
            
            for el in elementos:
                tit = el.get_text().strip()
                url = el.get('href', '')
                
                if not url.startswith('http') and url:
                    base = urlparse(f['u']).scheme + "://" + urlparse(f['u']).netloc
                    url = base + "/" + url.lstrip('/')
                
                # Criterio: Título largo y que contenga keywords
                if len(tit) > 20 and any(k in (tit + url).lower() for k in KEYWORDS):
                    if tit not in vistos:
                        datos += f"MEDIO: {f['n']} | CIUDAD: {f['r']} | NOTA: {tit} | URL: {url}\n\n"
                        vistos.add(tit)
        except: continue
    return datos

def procesar_con_ia(datos_raw, contexto):
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_final = next((m for m in modelos if 'flash' in m), modelos[0])
        model = genai.GenerativeModel(modelo_final)
        
        prompt = f"""
        FECHA: {fecha_hoy}. FUENTES: {contexto}.
        INSTRUCCIÓN: Prioriza 1. IMPUESTOS (unificar), 2. GOBIERNO, 3. ECONOMÍA.

        ORGANIZACIÓN: 
        1. COCHABAMBA (Incluir medios locales y noticias de TV sobre Cbba).
        2. SANTA CRUZ (Incluir medios locales y noticias de TV sobre SCZ).

        FORMATO ESTRICTO (No usar etiquetas como Resumen o Título):
        *TITULAR EN MAYÚSCULAS*
        NOMBRE DEL MEDIO EN MAYÚSCULAS
        Resumen de 5 líneas analizando el impacto.
        Enlace directo aquí.

        IMPORTANTE: Solo UN asterisco (*) antes y después del titular. El nombre del medio en la línea de abajo. Sin negritas dobles (**).
        """
        res = model.generate_content(prompt + "\n\nDATOS:\n" + datos_raw)
        return res.text
    except Exception as e:
        return f"Error en IA: {str(e)}"

# --- INTERFAZ ---
if api_key:
    genai.configure(api_key=api_key)
    c1, c2 = st.columns(2)
    
    with c1:
        if st.button('🚀 FASE 1: PRENSA Y TV (MÁXIMA CAPTURA)'):
            medios = [
                {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba"},
                {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "r": "Cochabamba"},
                {"n": "LA VOZ DE TARIJA", "u": "https://lavozdetarija.com/", "r": "Nacional"},
                {"n": "URGENTE.BO", "u": "https://www.urgente.bo/", "r": "Nacional"},
                {"n": "INNOTICIAS", "u": "https://innoticiasbo.com/", "r": "Cochabamba"},
                {"n": "ENFOQUE NEWS", "u": "https://enfoquenews.com.bo/", "r": "Cochabamba"},
                {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "r": "Santa Cruz"},
                {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "r": "Santa Cruz"},
                {"n": "UNITEL", "u": "https://unitel.bo/", "r": "Nacional"},
                {"n": "RED UNO", "u": "https://www.reduno.com.bo/", "r": "Nacional"},
                {"n": "BOLIVISIÓN", "u": "https://www.redbolivision.tv.bo/", "r": "Nacional"},
                {"n": "BOLIVIA TV", "u": "https://www.boliviatv.bo/", "r": "Nacional"},
                {"n": "PAT", "u": "https://www.pat.bo/", "r": "Nacional"},
                {"n": "RTP", "u": "https://www.rtpbolivia.com.bo/", "r": "Nacional"},
                {"n": "ATB", "u": "https://www.atb.com.bo/", "r": "Nacional"}
            ]
            datos = scraping_agresivo(medios)
            if datos:
                st.session_state.reporte_medios = procesar_con_ia(datos, "Prensa y TV")
            else:
                st.warning("No se capturaron datos. Los medios podrían estar bloqueando la conexión.")

    with c2:
        if st.button('📱 FASE 2: REDES SOCIALES (GOOGLE SEARCH)'):
            # Búsquedas directas en Google para saltar bloqueos de login de FB/X
            rrss = [
                {"n": "FB/X CBBA", "u": "https://www.google.com/search?q=impuestos+Cochabamba+site:facebook.com+OR+site:x.com&tbs=qdr:d", "r": "Cochabamba"},
                {"n": "IG/TK CBBA", "u": "https://www.google.com/search?q=gobierno+Cochabamba+site:instagram.com+OR+site:tiktok.com&tbs=qdr:d", "r": "Cochabamba"},
                {"n": "FB/X SCZ", "u": "https://www.google.com/search?q=impuestos+Santa+Cruz+site:facebook.com+OR+site:x.com&tbs=qdr:d", "r": "Santa Cruz"},
                {"n": "IG/TK SCZ", "u": "https://www.google.com/search?q=economia+Santa+Cruz+site:instagram.com+OR+site:tiktok.com&tbs=qdr:d", "r": "Santa Cruz"}
            ]
            datos_r = scraping_agresivo(rrss)
            if datos_r:
                st.session_state.reporte_rrss = procesar_con_ia(datos_r, "Redes Sociales")

    # --- DESPLIEGUE ---
    if st.session_state.reporte_medios:
        st.markdown("### 📰 REPORTE PRENSA Y TV")
        st.markdown(f'<div style="background:white;color:black;padding:25px;border:1px solid #ccc;font-family:serif;">{st.session_state.reporte_medios.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

    if st.session_state.reporte_rrss:
        st.markdown("---")
        st.markdown("### 📱 REPORTE REDES SOCIALES")
        st.markdown(f'<div style="background:#f9f9f9;color:black;padding:25px;border:1px solid #00acee;font-family:serif;">{st.session_state.reporte_rrss.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
else:
    st.info("Ingresa tu API Key para comenzar.")
