import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Estratégico Bolivia - Nacional", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# Configuración del Semáforo
CAT_RED = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda"]
CAT_YELLOW = ["economia", "dolar", "banco", "subvención", "finanzas"]
CAT_GREEN = ["gobierno", "ministro", "presidencia", "estado"]

KEYWORDS = CAT_RED + CAT_YELLOW + CAT_GREEN

def obtener_marca(texto):
    texto_l = texto.lower()
    if any(k in texto_l for k in CAT_RED): return "🔴"
    if any(k in texto_l for k in CAT_YELLOW): return "🟡"
    if any(k in texto_l for k in CAT_GREEN): return "🟢"
    return "⚪"

# --- 2. RASTREADOR DE PRENSA (NACIONAL Y REGIONAL) ---
def buscar_noticias():
    fuentes = [
        {"n": "LA RAZÓN", "u": "https://www.la-razon.com/", "r": "Nacional"},
        {"n": "EL DIARIO", "u": "https://www.eldiario.net/portal/", "r": "Nacional"},
        {"n": "ERBOL", "u": "https://erbol.com.bo/", "r": "Nacional"},
        {"n": "FIDES", "u": "https://www.radiofides.com/", "r": "Nacional"},
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
        {"n": "INNOTICIAS", "u": "https://innoticiasbo.com/", "r": "Nacional"},
        {"n": "ENFOQUE NEWS", "u": "https://enfoquenews.com.bo/", "r": "Nacional"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "r": "Santa Cruz"},
        {"n": "VISIÓN 360", "u": "https://www.vision360.bo/", "r": "Nacional"}
    ]
    
    hallazgos = ""
    enlaces_vistos = set()

    for f in fuentes:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            r = requests.get(f['u'], headers=headers, timeout=12)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')

            for el in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'a']):
                texto = el.get_text().strip()
                link = el.get('href', '') if el.name == 'a' else (el.find('a').get('href', '') if el.find('a') else '')
                
                if len(texto) > 35 and any(k in texto.lower() for k in KEYWORDS):
                    if link and link not in enlaces_vistos:
                        marca = obtener_marca(texto)
                        full_link = link if link.startswith('http') else f['u'].rstrip('/') + "/" + link.lstrip('/')
                        hallazgos += f"MARCA: {marca} | MEDIO: {f['n']} | REGIÓN: {f['r']} | NOTICIA: {texto} | LINK: {full_link}\n"
                        enlaces_vistos.add(link)
        except: continue
    return hallazgos

# --- 3. ANALISTA IA ---
def procesar_ia(datos_crudos):
    try:
        modelos_visibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_id = next((m for m in modelos_visibles if "1.5-flash" in m), modelos_visibles[0])
        model = genai.GenerativeModel(modelo_id)
        
        prompt = f"""
        FECHA: {fecha_hoy}. Reporte técnico nacional. 
        Clasifica las noticias por marca, primero ROJA, segundo AMARILLA, tercero VERDE. MANTÉN EL CÍRCULO DE COLOR (MARCA) al inicio de cada titular.

        FORMATO ESTRICTO, sin códigos o símbolos adicionales:
        [MARCA] *TITULAR EN MAYÚSCULAS Y NEGRITA*
        MEDIO EN MAYÚSCULAS Y NEGRITA
        Resumen técnico en 5 líneas, redacción periodística, no cambiar cargos ni nombres.
        Link sin etiqueta, formato de enlace.
        """
        res = model.generate_content(prompt + "\n\nDATOS:\n" + datos_crudos)
        return res.text
    except Exception as e:
        return f"Error en IA: {str(e)}"

# --- 4. INTERFAZ ---
st.title(f"Monitor Estratégico Bolivia: {fecha_hoy}")
api_key = st.sidebar.text_input("API Key Gemini:", type="password")

st.sidebar.markdown("""
**Leyenda de Marcas:**
🔴 Impuestos
🟡 Economía / Finanzas
🟢 Gobierno / Política
""")

st.header("1. Prensa y TV (Scraping Masivo)")
if api_key:
    genai.configure(api_key=api_key)
    if st.button("🚀 Iniciar Escaneo de Medios"):
        with st.spinner("Procesando noticias nacionales..."):
            datos = buscar_noticias()
            if datos:
                st.text_area("RESULTADOS:", value=procesar_ia(datos), height=600)
            else:
                st.warning("No se hallaron noticias relevantes hoy.")

st.divider()

# SECCIÓN 2: REDES SOCIALES
redes = ["Facebook", "X", "TikTok", "Instagram", "Threads"]

col_24h, col_1h = st.columns(2)

with col_24h:
    st.header("2. Redes Sociales (24h)")
    st.caption("Búsqueda nacional: IMPUESTOS BOLIVIA")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"🔗 [Ver en {r} (24h)](https://www.google.com/search?q={q}&tbs=qdr:d)")

with col_1h:
    st.header("3. Redes Sociales (1h)")
    st.caption("Búsqueda nacional: IMPUESTOS BOLIVIA")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"🔗 [Ver en {r} (1h)](https://www.google.com/search?q={q}&tbs=qdr:h)")
