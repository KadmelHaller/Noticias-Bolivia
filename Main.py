import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from googlesearch import search

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Estratégico Total", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "gobierno", "arce", "ministro", "economia", "dolar", "banco", "subvención", "combustible", "tarija"]

# --- FUNCIÓN SCRAPING MEDIOS ---
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
                    full_link = link if link.startswith('http') else f['u'].rstrip('/') + link
                    hallazgos += f"MEDIO: {f['n']} | REGIÓN: {f['r']} | NOTICIA: {texto} | LINK: {full_link}\n"
        except: continue
    return hallazgos

# --- FUNCIÓN IA (SOLUCIÓN 404) ---
def procesar_ia(datos_crudos):
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_id = next((m for m in modelos if "1.5-flash" in m), modelos[0])
        model = genai.GenerativeModel(modelo_id)
        
        prompt = f"""
        FECHA: {fecha_hoy}
        1. COCHABAMBA (Incluye Tarija y nacionales para esta zona)
        2. SANTA CRUZ (Incluye nacionales para esta zona)
        
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

# --- INTERFAZ STREAMLIT ---
st.title(f"Monitor Estratégico Total: {fecha_hoy}")
api_key = st.sidebar.text_input("API Key Gemini:", type="password")

# SECCIÓN 1: PRENSA ESCRITA Y TV
st.header("1. Monitoreo de Prensa y TV")
if api_key:
    genai.configure(api_key=api_key)
    if st.button("🚀 Iniciar Scraping de Medios"):
        with st.spinner("Rastreando medios..."):
            datos = buscar_noticias()
            if datos:
                resultado = procesar_ia(datos)
                st.text_area("RESULTADOS PRENSA (COPIAR):", value=resultado, height=500)
            else:
                st.warning("No se hallaron noticias en medios.")

st.divider()

# SECCIÓN 2: REDES SOCIALES (TU CÓDIGO ANIDADO)
st.header("2. Monitoreo de Redes e Influencers")
queries = [
    '"impuestos" "Cochabamba" site:facebook.com',
    '"impuestos" "Cochabamba" site:x.com',
    '"impuestos" "Cochabamba" site:instagram.com',
    '"impuestos" "Cochabamba" site:tiktok.com',
    '"impuestos" "Santa Cruz" site:facebook.com',
    '"impuestos" "Santa Cruz" site:x.com',
    '"impuestos" "Santa Cruz" site:instagram.com',
    '"impuestos" "Santa Cruz" site:tiktok.com'
]

if st.button("🔍 Iniciar Rastreo de Redes"):
    resultados_encontrados = []
    with st.spinner("Rastreando redes sociales..."):
        for q in queries:
            try:
                for res in search(q, lang="es", num=5, stop=5, pause=2, extra_params={'tbs': 'qdr:d'}):
                    blacklist = ["oferta", "precio", "vendo", "noticiero", "diario", "curso", "taller", "inscripciones"]
                    if not any(word in res.lower() for word in blacklist):
                        resultados_encontrados.append(res)
            except Exception as e:
                st.error(f"Error en {q}: {e}")

    links = list(set(resultados_encontrados))
    if not links:
        st.warning("No se encontraron menciones en redes sociales en las últimas 24h.")
    else:
        st.success(f"Se detectaron {len(links)} posibles menciones.")
        for link in links:
            st.markdown(f"📌 **Posible Opinión:** [Ver Publicación]({link})")
