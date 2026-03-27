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

# PRIORIDADES DE BÚSQUEDA (1. Impuestos, 2. Gobierno, 3. Economía)
KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "gobierno", "arce", "ministro", "estado", "economia", "dolar", "banco", "crisis"]

st.title(f"🔍 MONITOREO 24H: {fecha_hoy}")
st.markdown("### Prioridad: 1. Impuestos | 2. Gobierno | 3. Economía")
api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

def extraer_noticias():
    fuentes = [
        # COCHABAMBA
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "r": "Cochabamba", "t": "Escrito"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba", "t": "Escrito"},
        # SANTA CRUZ
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/economia", "r": "Santa Cruz", "t": "Escrito"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "r": "Santa Cruz", "t": "Escrito"},
        # TV Y DIGITAL
        {"n": "UNITEL", "u": "https://unitel.bo/", "r": "Nacional", "t": "TV"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/economia", "r": "Nacional", "t": "Digital"},
        # RRSS - LAS 4 BÚSQUEDAS (DISCOS)
        {"n": "FB/X CBBA", "u": "https://www.google.com/search?q=impuestos+Cochabamba+site:facebook.com+OR+site:x.com", "r": "Cochabamba", "t": "Redes Sociales"},
        {"n": "IG/TK CBBA", "u": "https://www.google.com/search?q=impuestos+Cochabamba+site:instagram.com+OR+site:tiktok.com", "r": "Cochabamba", "t": "Redes Sociales"},
        {"n": "FB/X SCZ", "u": "https://www.google.com/search?q=impuestos+Santa+Cruz+site:facebook.com+OR+site:x.com", "r": "Santa Cruz", "t": "Redes Sociales"},
        {"n": "IG/TK SCZ", "u": "https://www.google.com/search?q=impuestos+Santa+Cruz+site:instagram.com+OR+site:tiktok.com", "r": "Santa Cruz", "t": "Redes Sociales"}
    ]

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    acumulado = ""
    pb = st.progress(0)

    for i, f in enumerate(fuentes):
        st.write(f"📡 Escaneando: {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                tit = link.get_text().strip()
                url = link['href']
                if len(tit) > 25 and any(k in (tit + url).lower() for k in KEYWORDS):
                    acumulado += f"REGION: {f['r']} | MEDIO: {f['n']} | TIPO: {f['t']} | TITULO: {tit} | LINK: {url}\n\n"
        except: continue
    return acumulado

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 EJECUTAR MONITOREO AMPLIADO'):
        with st.status("Recopilando datos de 24 horas...") as status:
            raw_data = extraer_noticias()
            
            if len(raw_data) > 100:
                status.update(label="Analizando jerarquía de prioridades...", state="running")
                try:
                    # --- SOLUCIÓN AUTOMÁTICA AL ERROR 404 ---
                    # Listamos los modelos permitidos para tu API Key y tomamos el primero disponible
                    modelos_permitidos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    modelo_final = next((m for m in modelos_permitidos if 'flash' in m), modelos_permitidos[0])
                    
                    model = genai.GenerativeModel(modelo_final)
                    
                    prompt = f"""
                    FECHA: {fecha_hoy}. Eres un experto analista de prensa.
                    
                    JERARQUÍA DE CONTENIDO:
                    1. IMPUESTOS (Prioridad Máxima. Cambia 'Municipales/Nacionales' a 'IMPUESTOS').
                    2. GOBIERNO (Noticias de gestión, ministros, presidencia).
                    3. ECONOMÍA (Dólar, bancos, mercados).

                    ESTRUCTURA DEL REPORTE:
                    Organiza por 1. COCHABAMBA y 2. SANTA CRUZ.
                    Dentro de cada ciudad, clasifica por: 1.1 Escritos, 1.2 TV, 1.3 Digital, 1.4 Redes Sociales.
                    
                    CADA NOTICIA DEBE TENER:
                    TITULAR (MAYUS), MEDIO (MAYUS), Resumen de 4 a 6 líneas, LINK.
                    """
                    
                    res = model.generate_content(prompt + "\n\nNOTICIAS DETECTADAS:\n" + raw_data)
                    status.update(label=f"Reporte Finalizado con {modelo_final}", state="complete")
                    
                    st.markdown(f'''
                    <div style="background: white; color: black; padding: 30px; border: 1px solid #ddd; font-family: 'Times New Roman', serif; text-align: justify; line-height: 1.6;">
                        <h1 style="text-align: center; color: #1a3c5a;">REPORTE ESTRATÉGICO DIARIO</h1>
                        <hr>
                        {res.text.replace("\n", "<br>")}
                    </div>
                    ''', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error de conexión con la IA: {e}")
            else:
                st.warning("No se hallaron suficientes noticias. Intenta ampliar los términos de búsqueda.")
