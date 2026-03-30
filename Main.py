import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

st.set_page_config(page_title="Monitor Estratégico", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "gobierno", "arce", "ministro", "economia", "dolar", "banco", "subvención", "combustible", "tarija"]

def buscar_noticias():
    fuentes = [
        # Cochabamba / Tarija / Nacional
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba"},
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "r": "Cochabamba"},
        {"n": "LA VOZ DE TARIJA", "u": "https://lavozdetarija.com/", "r": "Tarija"},
        {"n": "UNITEL", "u": "https://unitel.bo/", "r": "Nacional"},
        {"n": "RTP", "u": "https://www.rtpbolivia.com.bo/", "r": "Nacional"},
        {"n": "BOLIVISIÓN", "u": "https://www.redbolivision.tv.bo/", "r": "Nacional"},
        {"n": "BOLIVIA TV", "u": "https://www.boliviatv.bo/", "r": "Nacional"},
        {"n": "ATB", "u": "https://www.atb.com.bo/", "r": "Nacional"},
        {"n": "RED UNO", "u": "https://www.reduno.com.bo/", "r": "Nacional"},
        {"n": "CADENA A", "u": "https://cadenaa.tv/", "r": "Nacional"},
        {"n": "URGENTE.BO", "u": "https://urgente.bo/", "r": "Nacional"},
        {"n": "INNOTICIAS", "u": "https://innoticiasbo.com/", "r": "Cochabamba"},
        {"n": "ENFOQUE NEWS", "u": "https://enfoquenews.com.bo/", "r": "Cochabamba"},
        # Santa Cruz
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "r": "Santa Cruz"},
        {"n": "VISIÓN 360", "u": "https://www.vision360.bo/", "r": "Santa Cruz"}
    ]
    
    hallazgos = ""
    for f in fuentes:
        try:
            r = requests.get(f['u'], headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
            soup = BeautifulSoup(r.text, 'html.parser')
            for el in soup.find_all(['h1', 'h2', 'h3', 'a']):
                texto = el.get_text().strip()
                link = el.get('href', '')
                if len(texto) > 30 and any(k in texto.lower() for k in KEYWORDS):
                    full_link = link if link.startswith('http') else f['u'].rstrip('/') + link
                    hallazgos += f"MEDIO: {f['n']} | REGIÓN: {f['r']} | NOTICIA: {texto} | LINK: {full_link}\n"
        except: continue
    return hallazgos

def procesar_ia(datos_crudos):
    try:
        # Solución Error 404: Usar identificación automática del modelo
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_id = next((m for m in modelos if "1.5-flash" in m), modelos[0])
        model = genai.GenerativeModel(modelo_id)
        
        prompt = f"""
        FECHA: {fecha_hoy}
        1. COCHABAMBA (Incluye Tarija y nacionales que afecten estas zonas)
        2. SANTA CRUZ (Incluye nacionales que afecten esta zona)
        
        FORMATO:
        **TITULAR EN MAYÚSCULAS**
        **MEDIO EN MAYÚSCULAS**
        Resumen técnico de 5 líneas sin cambios.
        Link directo.
        """
        res = model.generate_content(prompt + "\n\nDATOS:\n" + datos_crudos)
        return res.text
    except Exception as e:
        return f"Error: {str(e)}"

st.title(f"Monitor: {fecha_hoy}")
api_key = st.sidebar.text_input("API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    if st.button("🚀 INICIAR"):
        datos = buscar_noticias()
        if datos:
            resultado = procesar_ia(datos)
            st.text_area("RESULTADOS (COPIAR ABAJO):", value=resultado, height=700)
        else:
            st.warning("No hay noticias con esas keywords.")
