import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Estratégico Bolivia", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# Filtro de palabras clave
KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "gobierno", "arce", "ministro", "economia", "dolar", "banco", "subvención", "combustible", "tarija"]

# --- 2. RASTREADOR DE PRENSA Y TV (SCRAPING) ---
def buscar_noticias():
    fuentes = [
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
                    full_link = link if link.startswith('http') else f['u'].rstrip('/') + "/" + link.lstrip('/')
                    hallazgos += f"MEDIO: {f['n']} | REGIÓN: {f['r']} | NOTICIA: {texto} | LINK: {full_link}\n"
        except: continue
    return hallazgos

# --- 3. ANALISTA IA (CON SOLUCIÓN 404) ---
def procesar_ia(datos_crudos):
    try:
        modelos_visibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_id = next((m for m in modelos_visibles if "1.5-flash" in m), modelos_visibles[0])
        model = genai.GenerativeModel(modelo_id)
        
        prompt = f"""
        FECHA: {fecha_hoy}. Reporte técnico. 
        Divide en: 1. COCHABAMBA/TARIJA | 2. SANTA CRUZ. 

        FORMATO ESTRICTO:
        **TITULAR EN MAYÚSCULAS Y NEGRITA**
        **MEDIO EN MAYÚSCULAS Y NEGRITA**
        Resumen técnico en 5 líneas, redacción periodística, no cambiar cargos ni nombres mencionados en las notas en ningún caso.
        Link sin etiqueta, formato de enlace de Microsoft Word.
        """
        res = model.generate_content(prompt + "\n\nDATOS:\n" + datos_crudos)
        return res.text
    except Exception as e:
        return f"Error en IA: {str(e)}"

# --- 4. INTERFAZ ---
st.title(f"Monitor Estratégico: {fecha_hoy}")
api_key = st.sidebar.text_input("API Key Gemini:", type="password")

# SECCIÓN 1: PRENSA
st.header("1. Prensa y TV (Scraping Masivo)")
if api_key:
    genai.configure(api_key=api_key)
    if st.button("🚀 Iniciar Escaneo de Medios"):
        with st.spinner("Procesando noticias..."):
            datos = buscar_noticias()
            if datos:
                st.text_area("RESULTADOS DEL MONITOREO:", value=procesar_ia(datos), height=500)
            else:
                st.warning("No se hallaron noticias relevantes hoy.")
else:
    st.info("Ingresa tu API Key en la izquierda.")

st.divider()

# SECCIÓN 2: REDES (BÚSQUEDA INTELIGENTE SIN ERRORES)
st.header("2. Redes Sociales (Últimas 24h)")
st.caption("Haz clic en los enlaces para ver menciones de influencers y opinión pública:")

redes = ["Facebook", "X", "TikTok", "Instagram"]
col1, col2 = st.columns(2)

with col1:
    st.subheader("Cochabamba")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Cochabamba"')
        st.markdown(f"🔗 [Ver en {r}](https://www.google.com/search?q={q}&tbs=qdr:d)")

with col2:
    st.subheader("Santa Cruz")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Santa Cruz"')
        st.markdown(f"🔗 [Ver en {r}](https://www.google.com/search?q={q}&tbs=qdr:d)")

# SECCIÓN 3: REDES (ÚLTIMA HORA)
st.header("3. Redes Sociales (Última hora)")
st.caption("Haz clic en los enlaces para ver menciones de influencers y opinión pública:")

redes = ["Facebook", "X", "TikTok", "Instagram"]
col1, col2 = st.columns(2)

with col1:
    st.subheader("Cochabamba")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Cochabamba"')
        st.markdown(f"🔗 [Ver en {r}](https://www.google.com/search?q={q}&tbs=qdr:h)")

with col2:
    st.subheader("Santa Cruz")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Santa Cruz"')
        st.markdown(f"🔗 [Ver en {r}](https://www.google.com/search?q={q}&tbs=qdr:h)")

