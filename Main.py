import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import urllib.parse
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Estratégico Bolivia - Nacional", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy_str = datetime.now(zona_horaria).strftime('%d/%m/%Y')

KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "finanzas", "ministro"]
BLACKLIST_TOPICS = ["deporte", "fútbol", "farandula", "espectáculo", "show", "internacional", "mundial", "concierto", "cine", "entretenimiento"]

# --- 2. RASTREADOR DE PRENSA ---
def buscar_noticias():
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
    
    hallazgos = ""
    enlaces_vistos = set()

    for f in fuentes:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(f['u'], headers=headers, timeout=10)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')

            for el in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'a']):
                texto = el.get_text().strip()
                link = el.get('href', '') if el.name == 'a' else (el.find('a').get('href', '') if el.find('a') else '')
                texto_lower = texto.lower()
                
                if len(texto) > 35 and any(k in texto_lower for k in KEYWORDS):
                    if not any(b in texto_lower for b in BLACKLIST_TOPICS):
                        if link and link not in enlaces_vistos:
                            full_link = link if link.startswith('http') else f['u'].rstrip('/') + "/" + link.lstrip('/')
                            hallazgos += f"MEDIO: {f['n']} | NOTICIA: {texto} | LINK: {full_link}\n"
                            enlaces_vistos.add(link)
        except: continue
    return hallazgos

# --- 3. ANALISTA IA (PARCHE DE CUOTA REFORZADO) ---
def procesar_ia(datos_crudos):
    if not datos_crudos:
        return "No se encontraron noticias."
        
    # Obligamos a usar 1.5-flash para mayor estabilidad en Free Tier
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = f"""
    FECHA: {fecha_hoy_str}. Reporte técnico nacional BOLIVIA. 

    INSTRUCCIÓN:
    1. PROCESA CADA NOTA POR SEPARADO. NO AGRUPES.
    2. FORMATO: 
       *TITULAR EN MAYÚSCULAS*
       MEDIO EN MAYÚSCULAS
       Extrae palabra por palabra los primeros 2 a 3 párrafos del cuerpo de la nota, combinados en un solo parrafo, sin cambios en el texto para que sean entre 4 a 6 líneas, NADA MENOS.
       Enlace (URL sin etiquetas)
    """

    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            res = model.generate_content(prompt + "\n\nDATOS:\n" + datos_crudos)
            if res.text:
                return res.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                # Si es error de cuota, avisamos y esperamos un ciclo completo
                st.warning(f"Límite de API alcanzado. Esperando 60 segundos para reintentar (Intento {attempt+1}/{MAX_RETRIES})...")
                time.sleep(60)
                continue
            else:
                return f"Error crítico: {error_str}"
    
    return "No se pudo obtener respuesta de la IA tras varios intentos por límites de cuota de Google."

# --- 4. INTERFAZ ---
st.title(f"Monitor Estratégico Bolivia: {fecha_hoy_str}")
api_key = st.sidebar.text_input("API Key Gemini:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    if st.button("🚀 Iniciar Escaneo"):
        with st.spinner("Escaneando y procesando..."):
            datos = buscar_noticias()
            if datos:
                resultado = procesar_ia(datos)
                st.text_area("RESULTADOS:", value=resultado, height=600)
            else:
                st.info("No hay noticias hoy con esas palabras clave.")
else:
    st.info("Introduce tu API Key para comenzar.")

st.divider()

# SECCIÓN REDES
redes = ["Facebook", "X", "TikTok", "Instagram"]
cols = st.columns(len(redes))
for i, r in enumerate(redes):
    with cols[i]:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"[Ver {r}](https://www.google.com/search?q={q}&tbs=qdr:d)")
