import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Estratégico Bolivia - Semáforo", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# Configuración del Semáforo
CAT_RED = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda"]
CAT_YELLOW = ["economia", "dolar", "banco", "subvención", "precios", "finanzas"]
CAT_GREEN = ["gobierno", "arce", "ministro", "presidencia", "estado"]

KEYWORDS = CAT_RED + CAT_YELLOW + CAT_GREEN

def obtener_marca(texto):
    texto_l = texto.lower()
    if any(k in texto_l for k in CAT_RED): return "🔴"
    if any(k in texto_l for k in CAT_YELLOW): return "🟡"
    if any(k in texto_l for k in CAT_GREEN): return "🟢"
    return "⚪"

# --- 2. RASTREADOR DE PRENSA (AMPLIADO) ---
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
        FECHA: {fecha_hoy}. Reporte técnico. 
        Clasifica las noticias por región pero MANTÉN EL CÍRCULO DE COLOR (MARCA) al inicio de cada titular.
        Prioriza agrupar en: 1. NACIONAL/BOLIVIA | 2. COCHABAMBA/TARIJA | 3. SANTA CRUZ.

        FORMATO ESTRICTO:
        [MARCA] *TITULAR EN MAYÚSCULAS Y NEGRITA*
        MEDIO EN MAYÚSCULAS Y NEGRITA
        Resumen técnico en 5 líneas, redacción periodística, no cambiar cargos ni nombres.
        Link sin etiqueta, formato de enlace de Microsoft Word.
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
🔴 Impuestos / Fiscal
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
else:
    st.info("Ingresa tu API Key en la izquierda.")

st.divider()

# SECCIÓN 2 & 3: REDES (SE MANTIENE IGUAL)
for titulo, q_time in [("2. Redes Sociales (Últimas 24h)", "d"), ("3. Redes Sociales (Última hora)", "h")]:
    st.header(titulo)
    redes = ["Facebook", "X", "TikTok", "Instagram", "Threads"]
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Cochabamba")
        for r in redes:
            q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Cochabamba"')
            st.markdown(f"🔗 [Ver en {r}](https://www.google.com/search?q={q}&tbs=qdr:{q_time})")
    with col2:
        st.subheader("Santa Cruz")
        for r in redes:
            q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Santa Cruz"')
            st.markdown(f"🔗 [Ver en {r}](https://www.google.com/search?q={q}&tbs=qdr:{q_time})")
