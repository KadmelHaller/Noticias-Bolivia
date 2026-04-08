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
    
    lista_noticias = []
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
                            lista_noticias.append(f"MEDIO: {f['n']} | NOTICIA: {texto} | LINK: {full_link}")
                            enlaces_vistos.add(link)
        except: continue
    return lista_noticias

# --- 3. ANALISTA IA (PROCESAMIENTO POR LOTES) ---
def procesar_ia_por_lotes(lista_noticias):
    if not lista_noticias: return "No se encontraron noticias."
    
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_id = next((m for m in modelos if "1.5-flash" in m), modelos[0])
        model = genai.GenerativeModel(modelo_id)
        
        resultado_final = ""
        # Dividimos en lotes de 5 noticias para no saturar la cuota de tokens
        lote_size = 5
        lotes = [lista_noticias[i:i + lote_size] for i in range(0, len(lista_noticias), lote_size)]
        
        progreso = st.progress(0)
        for idx, lote in enumerate(lotes):
            datos_lote = "\n".join(lote)
            prompt = f"""
            FECHA ACTUAL: {fecha_hoy_str}. Reporte técnico nacional BOLIVIA. 
            NO AGRUPES. Procesa cada noticia individualmente.
            FORMATO:
            *TITULAR EN MAYÚSCULAS*
            MEDIO EN MAYÚSCULAS
            Extrae palabra por palabra los primeros 2 a 3 párrafos del cuerpo de la nota, combinados en un solo parrafo, sin cambios en el texto para que sean entre 4 a 6 líneas.
            Enlace (La URL sin etiquetas)
            ---
            """
            
            intentos = 0
            while intentos < 3:
                try:
                    res = model.generate_content(prompt + "\n\nDATOS:\n" + datos_lote)
                    resultado_final += res.text + "\n\n"
                    break
                except Exception as e:
                    if "429" in str(e):
                        time.sleep(15) # Pausa técnica si hay saturación
                        intentos += 1
                    else: raise e
            
            progreso.progress((idx + 1) / len(lotes))
            time.sleep(2) # Pausa de seguridad entre lotes
            
        return resultado_final
    except Exception as e:
        return f"Error crítico: {str(e)}"

# --- 4. INTERFAZ ---
st.title(f"Monitor Estratégico Bolivia: {fecha_hoy_str}")
api_key = st.sidebar.text_input("API Key Gemini:", type="password")

st.header("1. Prensa y TV (Scraping Masivo)")
if api_key:
    genai.configure(api_key=api_key)
    if st.button("🚀 Iniciar Escaneo"):
        with st.spinner("Procesando por lotes para evitar límites de API..."):
            noticias = buscar_noticias()
            if noticias:
                resultado = procesar_ia_por_lotes(noticias)
                st.text_area("RESULTADOS:", value=resultado, height=600)
            else:
                st.warning("No se hallaron noticias relevantes.")
else:
    st.info("Ingresa tu API Key.")

st.divider()

# SECCIÓN 2: REDES SOCIALES (ORIGINAL)
redes = ["Facebook", "X", "TikTok", "Instagram", "Threads"]
col_24h, col_1h = st.columns(2)

with col_24h:
    st.header("2. Redes Sociales (24h)")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"🔗 [Ver en {r} (24h)](https://www.google.com/search?q={q}&tbs=qdr:d)")

with col_1h:
    st.header("3. Redes Sociales (1h)")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"🔗 [Ver en {r} (1h)](https://www.google.com/search?q={q}&tbs=qdr:h)")
