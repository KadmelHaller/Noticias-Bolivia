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

# Keywords para captura amplia
KEYWORDS = [
    "impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "muni",
    "gobierno", "arce", "ministro", "estado", "presidencia", "alcalde", "gestión",
    "economia", "dolar", "banco", "crisis", "subvención", "combustible", "escasez"
]

if 'reporte_medios' not in st.session_state: st.session_state.reporte_medios = ""
if 'reporte_rrss' not in st.session_state: st.session_state.reporte_rrss = ""

st.title(f"🔍 MONITOR ESTRATÉGICO TOTAL: {fecha_hoy}")
api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

def scraping_fiel(fuentes):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': 'https://www.google.com/'
    }
    datos = ""
    pb = st.progress(0)
    for i, f in enumerate(fuentes):
        st.write(f"📡 Capturando datos de: {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Extraemos texto de enlaces y encabezados para no perder nada
            elementos = soup.find_all(['a', 'h1', 'h2', 'h3', 'h4'])
            vistos = set()
            
            for el in elementos:
                tit_original = el.get_text().strip()
                url = el.get('href', '')
                
                if url and not url.startswith('http'):
                    base = urlparse(f['u']).scheme + "://" + urlparse(f['u']).netloc
                    url = base + "/" + url.lstrip('/')
                
                if len(tit_original) > 22 and any(k in (tit_original + url).lower() for k in KEYWORDS):
                    if tit_original not in vistos:
                        # Enviamos el titular exacto a la IA
                        datos += f"MEDIO_ORIGEN: {f['n']} | CIUDAD: {f['r']} | TITULAR_EXACTO: {tit_original} | URL: {url}\n\n"
                        vistos.add(tit_original)
        except: continue
    return datos

def procesar_ia_fiel(datos_raw, contexto):
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_final = next((m for m in modelos if 'flash' in m), modelos[0])
        model = genai.GenerativeModel(modelo_final)
        
        prompt = f"""
        FECHA: {fecha_hoy}. FUENTES: {contexto}.
        PRIORIDAD: 1. IMPUESTOS (unificar término), 2. GOBIERNO, 3. ECONOMÍA.

        INSTRUCCIONES DE FIDELIDAD (CRÍTICO):
        1. TITULAR: Usa el TITULAR_EXACTO proporcionado, sin cambiar una sola letra ni puntuación.
        2. PERSONAS Y CARGOS: Identifica nombres de personas y sus cargos públicos/privados. Muéstralos EXACTAMENTE como aparecen en la noticia.
        3. ORGANIZACIÓN: Divide por 1. COCHABAMBA y 2. SANTA CRUZ.

        FORMATO VISUAL:
        *TITULAR EXACTO EN MAYÚSCULAS*
        NOMBRE DEL MEDIO EN MAYÚSCULAS
        Resumen de 5 líneas mencionando específicamente a los involucrados con sus cargos exactos.
        Enlace directo aquí.

        REGLA DE FORMATO: Solo UN asterisco (*) al inicio y final del titular. Nombre del medio en la línea de abajo. No uses etiquetas como 'Resumen:' o 'URL:'.
        """
        res = model.generate_content(prompt + "\n\nDATOS CAPTURADOS:\n" + datos_raw)
        return res.text
    except Exception as e:
        return f"Error en la IA: {str(e)}"

# --- ACCIONES ---

if api_key:
    genai.configure(api_key=api_key)
    c1, c2 = st.columns(2)
    
    with c1:
        if st.button('🚀 FASE 1: PRENSA, TV Y DIGITALES'):
            medios = [
                # COCHABAMBA
                {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba"},
                {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "r": "Cochabamba"},
                {"n": "INNOTICIAS", "u": "https://innoticiasbo.com/", "r": "Cochabamba"},
                {"n": "ENFOQUE NEWS", "u": "https://enfoquenews.com.bo/", "r": "Cochabamba"},
                # SANTA CRUZ Y NACIONAL
                {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "r": "Santa Cruz"},
                {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "r": "Santa Cruz"},
                {"n": "LA VOZ DIGITAL", "u": "https://lavoz.digital/", "r": "Santa Cruz"},
                {"n": "VISIÓN 360", "u": "https://www.vision360.bo/", "r": "Nacional/Santa Cruz"},
                {"n": "LA VOZ DE TARIJA", "u": "https://lavozdetarija.com/", "r": "Nacional"},
                {"n": "URGENTE.BO", "u": "https://www.urgente.bo/", "r": "Nacional"},
                # TV
                {"n": "UNITEL", "u": "https://unitel.bo/", "r": "Nacional"},
                {"n": "RED UNO", "u": "https://www.reduno.com.bo/", "r": "Nacional"},
                {"n": "BOLIVISIÓN", "u": "https://www.redbolivision.tv.bo/", "r": "Nacional"},
                {"n": "BOLIVIA TV", "u": "https://www.boliviatv.bo/", "r": "Nacional"},
                {"n": "PAT", "u": "https://www.pat.bo/", "r": "Nacional"},
                {"n": "RTP", "u": "https://www.rtpbolivia.com.bo/", "r": "Nacional"},
                {"n": "ATB", "u": "https://www.atb.com.bo/", "r": "Nacional"}
            ]
            datos_t = scraping_fiel(medios)
            if datos_t:
                st.session_state.reporte_medios = procesar_ia_fiel(datos_t, "Prensa y TV")

    with c2:
        if st.button('📱 FASE 2: REDES SOCIALES'):
            rrss_queries = [
                {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=impuestos+Cochabamba+site:facebook.com+OR+site:x.com&tbs=qdr:d", "r": "Cochabamba"},
                {"n": "RRSS SCZ", "u": "https://www.google.com/search?q=impuestos+Santa+Cruz+site:facebook.com+OR+site:x.com&tbs=qdr:d", "r": "Santa Cruz"}
            ]
            datos_r = scraping_fiel(rrss_queries)
            if datos_r:
                st.session_state.reporte_rrss = procesar_ia_fiel(datos_r, "Redes Sociales")

    # --- DESPLIEGUE ---
    if st.session_state.reporte_medios:
        st.markdown("### 📰 REPORTE FIDELIDAD: PRENSA Y TV")
        st.markdown(f'<div style="background:white;color:black;padding:30px;border:1px solid #ccc;font-family:serif;text-align:justify;">{st.session_state.reporte_medios.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

    if st.session_state.reporte_rrss:
        st.markdown("---")
        st.markdown("### 📱 REPORTE FIDELIDAD: REDES SOCIALES")
        st.markdown(f'<div style="background:#fcfcfc;color:black;padding:30px;border:1px solid #00acee;font-family:serif;text-align:justify;">{st.session_state.reporte_rrss.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
else:
    st.info("Ingresa tu API Key para activar el monitoreo.")
