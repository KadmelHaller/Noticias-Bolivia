import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
from urllib.parse import urlparse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Monitoreo Tributario Bolivia", page_icon="🇧🇴", layout="wide")

zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')

# Filtros enfocados 100% en IMPUESTOS
TEMAS_OK = ["impuesto", "sin", "tribut", "factur", "fiscal", "recaudaci", "clausur", "presupuesto", "aduana", "econom", "dolar", "banco", "gobierno"]

def es_relevante(texto, url):
    txt = (texto + url).lower()
    # Evitar noticias de años pasados
    if any(old in txt for old in ["2021", "2022", "2023", "2024"]): return False
    return any(t in txt for t in TEMAS_OK)

st.title(f"📰 MONITOREO TRIBUTARIO: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_fuentes():
    fuentes = [
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "r": "Cochabamba"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "r": "Santa Cruz"},
        {"n": "UNITEL", "u": "https://unitel.bo/noticias/economia", "r": "Nacional"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/economia", "r": "Nacional"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}
    data_final = ""
    pb = st.progress(0)
    
    for i, f in enumerate(fuentes):
        st.write(f"📡 Buscando en: {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            vistos = 0
            
            for l in links:
                url_raw = l['href']
                url = url_raw if url_raw.startswith('http') else urlparse(f['u']).scheme + "://" + urlparse(f['u']).netloc + "/" + url_raw.lstrip('/')
                
                if "google.com" in url or len(url) < 35: continue
                
                titulo = l.get_text().strip()
                if len(titulo) < 30: continue

                if es_relevante(titulo, url):
                    try:
                        rn = requests.get(url, headers=headers, timeout=5)
                        s_n = BeautifulSoup(rn.text, 'html.parser')
                        parrafos = [p.get_text().strip() for p in s_n.find_all('p') if len(p.get_text()) > 60]
                        txt_cuerpo = " ".join(parrafos[:2]) # Solo 2 párrafos para no saturar
                        
                        if len(txt_cuerpo) > 50:
                            data_final += f"REGION: {f['r']} | MEDIO: {f['n']} | TITULAR: {titulo} | TXT: {txt_cuerpo[:400]} | LINK: {url}\n\n"
                            vistos += 1
                    except: continue
                if vistos >= 4: break 
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE UNIFICADO'):
        with st.status("Escaneando medios...") as status:
            raw_data = procesar_fuentes()
            
            if len(raw_data) > 50:
                status.update(label="Analizando con IA (Modo Auto-Detección)...", state="running")
                
                # --- LÓGICA ANTI-ERROR 404 ---
                try:
                    # 1. Intentamos obtener la lista de modelos disponibles en TU cuenta
                    modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    
                    # 2. Buscamos el mejor candidato (flash es prioridad)
                    # Si 'models/gemini-1.5-flash' está, lo usamos; si no, el primero que aparezca.
                    modelo_final = next((m for m in modelos_disponibles if 'gemini-1.5-flash' in m), modelos_disponibles[0])
                    
                    model = genai.GenerativeModel(modelo_final)
                    
                    prompt = f"""
                    FECHA: {fecha_hoy_bonita}. Eres un analista de prensa especializado en Bolivia.
                    INSTRUCCIÓN DE NOMENCLATURA: Cambia 'Impuestos Municipales', 'Impuestos Nacionales' o 'Tributos' a la palabra única 'IMPUESTOS'.
                    
                    ORGANIZACIÓN: 1. COCHABAMBA, 2. SANTA CRUZ.
                    FORMATO: TITULAR (MAYUS), MEDIO (MAYUS), resumen de 4 líneas enfocado en IMPUESTOS, URL.
                    """
                    
                    res = model.generate_content(prompt + "\n\nDATOS:\n" + raw_data)
                    
                    status.update(label=f"Reporte Listo (Usando {modelo_final})", state="complete")
                    
                    # Formateo visual
                    processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                    st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                
                except Exception as e:
                    st.error(f"Error crítico: {e}. Por favor, verifica tu API Key o ejecuta 'pip install -U google-generativeai' en tu terminal.")
            else:
                st.warning("No se encontraron noticias nuevas con el filtro de 'IMPUESTOS' en las portadas.")
