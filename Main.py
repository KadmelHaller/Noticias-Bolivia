import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import urllib.parse
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Estratégico Bolivia", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy_str = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# Filtros más amplios para asegurar captura
KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "finanzas", "ministro", "económ", "itf", "dólar", "aduana", "presupuesto"]
BLACKLIST_TOPICS = ["deporte", "fútbol", "farandula", "espectáculo", "show", "internacional", "mundial", "concierto", "cine", "entretenimiento"]

# --- 2. RASTREADOR DE PRENSA (TODOS TUS MEDIOS) ---
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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    for f in fuentes:
        try:
            r = requests.get(f['u'], headers=headers, timeout=12)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')

            # Buscamos en enlaces y también en contenedores comunes de titulares
            for el in soup.find_all(['a', 'h1', 'h2', 'h3']):
                texto = el.get_text().strip()
                link = el.get('href', '') if el.name == 'a' else (el.find('a').get('href', '') if el.find('a') else '')
                
                texto_lower = texto.lower()
                
                if len(texto) > 25 and any(k in texto_lower for k in KEYWORDS):
                    if not any(b in texto_lower for b in BLACKLIST_TOPICS):
                        if link and link not in enlaces_vistos:
                            full_link = link if link.startswith('http') else f['u'].rstrip('/') + "/" + link.lstrip('/')
                            lista_noticias.append(f"MEDIO: {f['n']} | NOTICIA: {texto} | LINK: {full_link}")
                            enlaces_vistos.add(link)
        except: continue
    return lista_noticias

# --- 3. ANALISTA IA (BATCHING DE SEGURIDAD) ---
def procesar_ia(noticias_lista, key):
    if not noticias_lista: return "No se hallaron noticias con los criterios actuales."
    
    genai.configure(api_key=key)
    # Detección dinámica de modelo
    modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    modelo_id = next((m for m in modelos if "flash" in m), modelos[0])
    model = genai.GenerativeModel(modelo_id)
    
    reporte = ""
    # Procesar de 3 en 3 para evitar errores 429
    for i in range(0, len(noticias_lista), 3):
        bloque = "\n".join(noticias_lista[i:i+3])
        prompt = f"""
        FECHA: {fecha_hoy_str}. Reporte técnico nacional BOLIVIA.
        INSTRUCCIÓN: Procesa cada noticia individualmente. NO AGRUPES.
        FORMATO POR NOTICIA:
        *TITULAR EN MAYÚSCULAS*
        MEDIO EN MAYÚSCULAS
        Resumen de 4 a 6 líneas detallando el impacto económico o fiscal.
        URL
        ---
        DATOS CRUDOS:
        {bloque}
        """
        try:
            res = model.generate_content(prompt)
            reporte += res.text + "\n\n"
            time.sleep(1.5) # Pausa mínima antipánico
        except Exception as e:
            if "429" in str(e):
                time.sleep(10) # Si hay saturación, esperamos
            reporte += f"\n(Error en bloque: {str(e)})\n"
            
    return reporte

# --- 4. INTERFAZ ---
st.title(f"Monitor Estratégico Bolivia: {fecha_hoy_str}")
api_key = st.sidebar.text_input("Gemini API Key:", type="password")

if st.button("🚀 Iniciar Escaneo"):
    if not api_key:
        st.error("Introduce la API Key")
    else:
        with st.spinner("Rastreando medios..."):
            datos = buscar_noticias()
            if datos:
                st.info(f"Hallazgos crudos: {len(datos)}")
                reporte_ia = procesar_ia(datos, api_key)
                st.text_area("REPORTE:", value=reporte_ia, height=600)
            else:
                st.warning("No se encontraron noticias. Intenta ampliar los filtros.")

st.divider()

# --- 5. REDES SOCIALES ---
st.header("Pulso en Redes Sociales")
redes = ["Facebook", "X", "TikTok", "Instagram", "Threads"]
c1, c2 = st.columns(2)
with c1:
    st.subheader("Últimas 24h")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"🔗 [Ver en {r}](https://www.google.com/search?q={q}&tbs=qdr:d)")
with c2:
    st.subheader("Última hora")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"🔗 [Ver en {r}](https://www.google.com/search?q={q}&tbs=qdr:h)")
