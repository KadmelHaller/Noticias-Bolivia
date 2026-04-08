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

# FILTRO DE EXCLUSIÓN (Lo que NO queremos ver)
# Se eliminan deportes, farándula, espectáculos e internacional.
BLACKLIST = [
    "fútbol", "deporte", "partido", "gol", "atletismo", "fifa", "conmebol", "copa", "liga", "tenis",
    "farándula", "espectáculo", "show", "concierto", "cine", "actor", "actriz", "música", "estreno",
    "internacional", "mundo", "eeuu", "rusia", "ucrania", "israel", "gaza", "china", "europa", "venezuela"
]

# --- 2. RASTREADOR DE COBERTURA NACIONAL TOTAL ---
def buscar_todas_las_noticias():
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
    vistos = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for f in fuentes:
        try:
            r = requests.get(f['u'], headers=headers, timeout=10)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')

            # Capturamos titulares de enlaces y encabezados
            for tag in soup.find_all(['a', 'h1', 'h2', 'h3']):
                texto = tag.get_text().strip()
                link = tag.get('href', '') if tag.name == 'a' else (tag.find('a').get('href', '') if tag.find('a') else '')
                
                t_low = texto.lower()
                
                # REGLA: Si es largo y NO está en la lista negra, pasa.
                if len(texto) > 30:
                    if not any(b in t_low for b in BLACKLIST):
                        if link and link not in vistos:
                            full_link = link if link.startswith('http') else f['u'].rstrip('/') + "/" + link.lstrip('/')
                            hallazgos.append(f"MEDIO: {f['n']} | NOTICIA: {texto} | LINK: {full_link}")
                            vistos.add(link)
        except: continue
    return hallazgos

# --- 3. ANALISTA IA (PROCESAMIENTO POR LOTES) ---
def procesar_ia(datos, api_key):
    if not datos: return "No se encontraron noticias nacionales bajo los criterios de exclusión."
    
    genai.configure(api_key=api_key)
    # Detección de modelo disponible
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    sel_model = next((m for m in models if "flash" in m), models[0])
    model = genai.GenerativeModel(sel_model)
    
    resultado = ""
    # Lotes de 3 para proteger la cuota
    for i in range(0, len(datos), 3):
        bloque = "\n".join(datos[i:i+3])
        prompt = f"""
        FECHA ACTUAL: {fecha_hoy_str}. Reporte de prensa nacional de BOLIVIA.
        
        INSTRUCCIONES:
        1. Procesa cada noticia individualmente. NO LAS AGRUPES.
        2. Omite cualquier noticia que sea de deportes, farándula o internacional.
        3. Si la noticia es de política, economía, sociedad, justicia o seguridad de BOLIVIA, inclúyela.
        
        FORMATO:
        *TITULAR EN MAYÚSCULAS*
        MEDIO EN MAYÚSCULAS
        Extrae un párrafo de 4 a 6 líneas que resuma el contenido de la nota.
        URL
        ---
        """
        try:
            res = model.generate_content(prompt + "\n\nDATOS:\n" + bloque)
            resultado += res.text + "\n\n"
            time.sleep(2) # Pausa técnica para evitar error 429
        except Exception as e:
            if "429" in str(e): time.sleep(10)
            resultado += f"\n[Error en bloque: {str(e)}]\n"
            
    return resultado

# --- 4. INTERFAZ ---
st.title(f"Monitor Nacional Bolivia: {fecha_hoy_str}")
st.caption("Filtro automático: Excluye Deportes, Farándula e Internacional.")

key = st.sidebar.text_input("Gemini API Key:", type="password")

if st.button("🚀 Iniciar Escaneo Nacional"):
    if not key:
        st.error("Introduce tu API Key en la barra lateral.")
    else:
        with st.spinner("Rastreando todos los medios nacionales..."):
            noticias_crudas = buscar_todas_las_noticias()
            if noticias_crudas:
                st.success(f"Se capturaron {len(noticias_crudas)} noticias potenciales.")
                reporte = procesar_ia(noticias_crudas, key)
                st.text_area("REPORTE FINAL:", value=reporte, height=600)
            else:
                st.warning("No se hallaron noticias que superen el filtro de exclusión.")

st.divider()

# BLOQUE DE REDES (SE MANTIENE)
st.header("Monitoreo de Redes Sociales")
redes = ["Facebook", "X", "TikTok", "Instagram", "Threads"]
col1, col2 = st.columns(2)
with col1:
    st.subheader("Búsqueda 24h")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "Bolivia"')
        st.markdown(f"🔗 [Ver en {r} (24h)](https://www.google.com/search?q={q}&tbs=qdr:d)")
with col2:
    st.subheader("Búsqueda 1h")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "Bolivia"')
        st.markdown(f"🔗 [Ver en {r} (1h)](https://www.google.com/search?q={q}&tbs=qdr:h)")
