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

api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

def scraping_generico(lista_fuentes):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    acumulado = ""
    pb = st.progress(0)
    for i, f in enumerate(lista_fuentes):
        st.write(f"📡 Escaneando: {f['n']}...")
        pb.progress((i + 1) / len(lista_fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                tit = link.get_text().strip()
                url = link['href']
                if len(tit) > 25 and any(k in (tit + url).lower() for k in KEYWORDS):
                    acumulado += f"REGION: {f['r']} | MEDIO: {f['n']} | TIPO: {f['t']} | TITULO: {tit} | LINK: {url}\n\n"
        except: continue
    return acumulado

def generar_con_ia(datos_brutos, contexto_tipo):
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_final = next((m for m in modelos if 'flash' in m), modelos[0])
        model = genai.GenerativeModel(modelo_final)
        
        prompt = f"""
        FECHA: {fecha_hoy}. TIPO DE FUENTES: {contexto_tipo}.
        PRIORIDAD: 1. IMPUESTOS (unificar término), 2. GOBIERNO, 3. ECONOMÍA.
        ORGANIZACIÓN: Por ciudad (Cochabamba, Santa Cruz) y tipo de medio (1.1 a 1.4).
        FORMATO: TITULAR (MAYUS), MEDIO (MAYUS), Resumen 5 líneas, LINK.
        """
        res = model.generate_content(prompt + "\n\nDATOS:\n" + datos_brutos)
        return res.text
    except Exception as e:
        return f"Error en IA: {str(e)}"

# --- INTERFAZ ---

if api_key:
    genai.configure(api_key=api_key)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button('🚀 FASE 1: ANALIZAR MEDIOS (Escritos/TV/Digital)'):
            fuentes_medios = [
                {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "r": "Cochabamba", "t": "Escrito"},
                {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba", "t": "Escrito"},
                {"n": "EL DEBER", "u": "https://eldeber.com.bo/economia", "r": "Santa Cruz", "t": "Escrito"},
                {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "r": "Santa Cruz", "t": "Escrito"},
                {"n": "UNITEL", "u": "https://unitel.bo/", "r": "Nacional", "t": "TV"},
                {"n": "URGENTE.BO", "u": "https://www.urgente.bo/economia", "r": "Nacional", "t": "Digital"}
            ]
            datos = scraping_generico(fuentes_medios)
            if datos:
                st.session_state.reporte_medios = generar_con_ia(datos, "Medios Tradicionales")
            else:
                st.warning("No se hallaron noticias en medios.")

    with col2:
        if st.button('📱 FASE 2: AGREGAR REDES SOCIALES (FB/X/IG/TK)'):
            fuentes_rrss = [
                {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=impuestos+Cochabamba+site:facebook.com+OR+site:x.com", "r": "Cochabamba", "t": "Redes Sociales"},
                {"n": "RRSS SCZ", "u": "https://www.google.com/search?q=impuestos+Santa+Cruz+site:instagram.com+OR+site:tiktok.com", "r": "Santa Cruz", "t": "Redes Sociales"}
            ]
            datos_rrss = scraping_generico(fuentes_rrss)
            if datos_rrss:
                st.session_state.reporte_rrss = generar_con_ia(datos_rrss, "Redes Sociales (Escaneo Directo)")
            else:
                st.warning("No se hallaron menciones en redes sociales.")

    # --- MOSTRAR RESULTADOS (Siempre visibles si existen) ---
    
    if st.session_state.reporte_medios:
        st.markdown("### 📰 RESULTADOS: MEDIOS ESCRITOS, TV Y DIGITAL")
        st.markdown(f'<div style="background: white; color: black; padding: 20px; border-left: 5px solid #1a3c5a; font-family: serif; margin-bottom: 20px;">{st.session_state.reporte_medios.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

    if st.session_state.reporte_rrss:
        st.markdown("### 📱 RESULTADOS: RELEVAMIENTO DE REDES SOCIALES")
        st.markdown(f'<div style="background: #f0f8ff; color: black; padding: 20px; border-left: 5px solid #00acee; font-family: serif;">{st.session_state.reporte_rrss.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
else:
    st.info("Por favor, ingresa tu API Key en la barra lateral para comenzar.")
