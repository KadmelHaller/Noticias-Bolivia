import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import urllib.parse
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Nacional Bolivia", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy_str = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# FILTRO DE EXCLUSIÓN (Omite deportes, farándula, espectáculo e internacional)
BLACKLIST = [
    "fútbol", "deporte", "partido", "gol", "atletismo", "fifa", "conmebol", "copa", "liga", "tenis",
    "farándula", "espectáculo", "show", "concierto", "cine", "actor", "actriz", "música", "estreno",
    "internacional", "mundo", "eeuu", "rusia", "ucrania", "israel", "gaza", "china", "europa", "venezuela"
]

# --- 2. RASTREADOR OPTIMIZADO ---
def buscar_noticias_fast():
    fuentes = [
        {"n": "LA RAZÓN", "u": "https://www.la-razon.com/"},
        {"n": "EL DIARIO", "u": "https://www.eldiario.net/portal/"},
        {"n": "ERBOL", "u": "https://erbol.com.bo/"},
        {"n": "EJU.TV", "u": "https://eju.tv/"},
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/"},
        {"n": "LA VOZ DE TARIJA", "u": "https://lavozdetarija.com/"},
        {"n": "UNITEL", "u": "https://unitel.bo/"},
        {"n": "RTP", "u": "https://www.rtpbolivia.com.bo/"},
        {"n": "BOLIVISIÓN", "u": "https://www.redbolivision.tv.bo/"},
        {"n": "BOLIVIA TV", "u": "https://www.boliviatv.bo/"},
        {"n": "ATB", "u": "https://www.atb.com.bo/"},
        {"n": "RED UNO", "u": "https://www.reduno.com.bo/"},
        {"n": "CADENA A", "u": "https://cadenaa.tv/"},
        {"n": "URGENTE.BO", "u": "https://urgente.bo/"},
        {"n": "INNOTICIAS", "u": "https://innoticiasbo.com/"},
        {"n": "ENFOQUE NEWS", "u": "https://enfoquenews.com.bo/"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/"},
        {"n": "VISIÓN 360", "u": "https://www.vision360.bo/"}
    ]
    
    hallazgos = []
    vistos_texto = set()
    headers = {'User-Agent': 'Mozilla/5.0'}

    for f in fuentes:
        try:
            r = requests.get(f['u'], headers=headers, timeout=5)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')

            for tag in soup.find_all(['a', 'h1', 'h2', 'h3']):
                texto = tag.get_text().strip()
                link = tag.get('href', '') if tag.name == 'a' else (tag.find('a').get('href', '') if tag.find('a') else '')
                t_low = texto.lower()
                
                if len(texto) > 40 and t_low not in vistos_texto:
                    if not any(b in t_low for b in BLACKLIST):
                        full_link = link if link.startswith('http') else f['u'].rstrip('/') + "/" + link.lstrip('/')
                        hallazgos.append(f"MEDIO: {f['n']} | NOTICIA: {texto} | LINK: {full_link}")
                        vistos_texto.add(t_low)
        except: continue
    
    return hallazgos[:40]

# --- 3. ANALISTA IA ---
def procesar_ia_safe(datos, api_key):
    genai.configure(api_key=api_key)
    modelos_visibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    modelo_id = next((m for m in modelos_visibles if "flash" in m), modelos_visibles[0])
    model = genai.GenerativeModel(modelo_id)
    
    reporte = ""
    for i in range(0, len(datos), 5):
        bloque = "\n".join(datos[i:i+5])
        prompt = f"RESUMEN NACIONAL BOLIVIA {fecha_hoy_str}. No deportes/farandula/internacional. FORMATO: *TITULAR*, MEDIO, RESUMEN 4-6 LÍNEAS, URL."
        try:
            res = model.generate_content(prompt + "\n\nDATOS:\n" + bloque)
            reporte += res.text + "\n\n---\n\n"
            time.sleep(2)
        except:
            time.sleep(5)
            continue
    return reporte

# --- 4. INTERFAZ ---
st.title(f"Monitor Nacional Bolivia: {fecha_hoy_str}")

with st.sidebar:
    api_key = st.sidebar.text_input("API Key Gemini:", type="password")

if st.button("🚀 Iniciar Escaneo Nacional"):
    if not api_key:
        st.error("Ingresa tu API Key en la izquierda.")
    else:
        with st.spinner("Procesando noticias nacionales..."):
            seleccion = buscar_noticias_fast()
            if seleccion:
                resultado = procesar_ia_safe(seleccion, api_key)
                st.text_area("RESULTADOS:", value=resultado, height=600)
            else:
                st.warning("No se hallaron noticias relevantes.")

st.divider()

# --- 5. REDES SOCIALES (FORMATO ORIGINAL RESTABLECIDO) ---
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
