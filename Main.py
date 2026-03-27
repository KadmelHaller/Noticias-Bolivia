import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re

st.set_page_config(page_title="Monitor Tributario 24h", page_icon="🇧🇴", layout="wide")

zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# --- CONFIGURACIÓN DE BÚSQUEDA ---
KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "aduana", "econom", "recauda", "muni"]

st.title(f"🔍 RELEVAMIENTO TRIBUTARIO 24H: {fecha_hoy}")
api_key = st.sidebar.text_input("Gemini API Key:", type="password")

def buscar_noticias():
    fuentes = [
        # PORTADAS Y SECCIONES (CBBA)
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "r": "Cochabamba", "t": "Escrito"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/seccion/cochabamba/", "r": "Cochabamba", "t": "Escrito"},
        # PORTADAS Y SECCIONES (SCZ)
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/economia", "r": "Santa Cruz", "t": "Escrito"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/category/economia/", "r": "Santa Cruz", "t": "Escrito"},
        # TV Y DIGITAL
        {"n": "UNITEL", "u": "https://unitel.bo/noticias/economia", "r": "Nacional", "t": "TV"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/economia", "r": "Nacional", "t": "Digital"},
        # BÚSQUEDAS GOOGLE RRSS (TUS 4 DISCOS)
        {"n": "FB CBBA", "u": "https://www.google.com/search?q=site:facebook.com+impuestos+Cochabamba+2026", "r": "Cochabamba", "t": "RRSS"},
        {"n": "X/IG SCZ", "u": "https://www.google.com/search?q=site:x.com+OR+site:instagram.com+impuestos+Santa+Cruz+2026", "r": "Santa Cruz", "t": "RRSS"},
        {"n": "TK/FB SCZ", "u": "https://www.google.com/search?q=site:tiktok.com+OR+site:facebook.com+impuestos+Santa+Cruz+2026", "r": "Santa Cruz", "t": "RRSS"}
    ]

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    txt_acumulado = ""
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
                if len(tit) > 20 and any(k in (tit + url).lower() for k in KEYWORDS):
                    txt_acumulado += f"CIUDAD: {f['r']} | MEDIO: {f['n']} | TIPO: {f['t']} | NOTA: {tit} | URL: {url}\n\n"
        except: continue
    return txt_acumulado

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 INICIAR ESCANEO TOTAL'):
        with st.status("Buscando noticias e hilos de RRSS...") as status:
            datos = buscar_noticias()
            
            if len(datos) > 100:
                status.update(label="Conectando con IA (Modo Auto-Detección)...", state="running")
                try:
                    # --- SOLUCIÓN FINAL AL ERROR 404 ---
                    # Listamos todos los modelos y agarramos el primero que sirva para generar texto
                    modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    # Priorizamos flash si existe, si no, el primero de la lista
                    nombre_modelo = next((m for m in modelos if 'flash' in m), modelos[0])
                    
                    model = genai.GenerativeModel(nombre_modelo)
                    
                    prompt = f"""
                    Hoy es {fecha_hoy}. Eres un analista de prensa experto.
                    INSTRUCCIÓN: Cambia 'Impuestos Municipales' o 'Nacionales' a la palabra única 'IMPUESTOS'.
                    
                    ORDENA EL REPORTE ASÍ:
                    1. COCHABAMBA (1.1 Escritos, 1.2 TV, 1.3 Digital, 1.4 Redes Sociales)
                    2. SANTA CRUZ (1.1 Escritos, 1.2 TV, 1.3 Digital, 1.4 Redes Sociales)
                    
                    CADA NOTICIA: TÍTULO (MAYUS), MEDIO (MAYUS), resumen 4 líneas sobre IMPUESTOS y LINK.
                    """
                    
                    res = model.generate_content(prompt + "\n\nDATOS:\n" + datos)
                    status.update(label=f"Reporte listo (Modelo: {nombre_modelo})", state="complete")
                    
                    st.markdown(f'''
                    <div style="background: white; color: black; padding: 25px; border: 1px solid #000; font-family: serif; text-align: justify;">
                        {res.text.replace("\n", "<br>")}
                    </div>
                    ''', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error definitivo de IA: {e}")
            else:
                st.warning("No se hallaron noticias. Intenta ampliar las palabras clave.")
