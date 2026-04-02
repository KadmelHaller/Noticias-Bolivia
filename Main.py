import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import urllib.parse
import re

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Estratégico Bolivia - Nacional", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_str = ahora.strftime('%d/%m/%Y')
# Para filtro de URL (ej: 2026/04/02 o 2026-04-02)
patron_fecha_url = ahora.strftime('%Y/%m/%d')
patron_fecha_alt = ahora.strftime('%Y-%m-%d')

# Filtros de contenido
KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "economia", "dolar", "banco", "subvención", "finanzas", "gobierno", "ministro", "presidencia", "estado"]
BLACKLIST_TOPICS = ["deporte", "fútbol", "farandula", "espectáculo", "show", "internacional", "mundial", "concierto", "cine", "entretenimiento"]

# --- 2. RASTREADOR DE PRENSA (ORDENADO POR MEDIO Y ESTRICTO 24H) ---
def buscar_noticias():
    fuentes = [
        {"n": "LA RAZÓN", "u": "https://www.la-razon.com/", "r": "Nacional"},
        {"n": "EL DIARIO", "u": "https://www.eldiario.net/portal/", "r": "Nacional"},
        {"n": "ERBOL", "u": "https://erbol.com.bo/", "r": "Nacional"},
        {"n": "FIDES", "u": "https://www.radiofides.com/", "r": "Nacional"},
        {"n": "EJU.TV", "u": "https://eju.tv/", "r": "Nacional"},
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
    
    fuentes = sorted(fuentes, key=lambda x: x['n'])
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
                
                texto_lower = texto.lower()
                
                # 1. Filtro de Relevancia y Blacklist
                if len(texto) > 35 and any(k in texto_lower for k in KEYWORDS):
                    if not any(b in texto_lower for b in BLACKLIST_TOPICS):
                        
                        # 2. Filtro Estricto de 24 Horas
                        # Verificamos si la URL contiene la fecha de hoy o ayer, o si el texto menciona inmediatez
                        es_reciente = any(x in link for x in [patron_fecha_url, patron_fecha_alt]) or \
                                      any(t in texto_lower for t in ["hoy", "hace", "minuto", "última hora"])
                        
                        if es_reciente and link and link not in enlaces_vistos:
                            full_link = link if link.startswith('http') else f['u'].rstrip('/') + "/" + link.lstrip('/')
                            hallazgos += f"MEDIO: {f['n']} | REGIÓN: {f['r']} | NOTICIA: {texto} | LINK: {full_link}\n"
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
        FECHA: {fecha_hoy_str}. Reporte técnico nacional BOLIVIA. 
        Muestra todas las noticias nacionales encontradas. 
        PROHIBIDO: noticias de deportes, farándula, espectáculos o internacionales.
        ESTRICTO: Solo noticias publicadas en las últimas 24 horas.
        ORDEN: Agrupa y presenta las noticias por MEDIO DE COMUNICACIÓN en orden alfabético.

        En cabecera muestra una sola vez:
        🔴 Impuestos / Fiscal, 🟡 Economía / Finanzas, 🟢 Gobierno / Política

        FORMATO ESTRICTO SIN SÍMBOLOS ADICIONALES:
        *TITULAR EN MAYÚSCULAS Y NEGRITA*
        MEDIO EN MAYÚSCULAS Y NEGRITA
        Resumen técnico real en 4 a 6 líneas, redacción periodística estricta, no cambiar ni acortar cargos ni nombres de las notas.
        Link sin etiqueta.
        """
        res = model.generate_content(prompt + "\n\nDATOS:\n" + datos_crudos)
        return res.text
    except Exception as e:
        return f"Error en IA: {str(e)}"

# --- 4. INTERFAZ ---
st.title(f"Monitor Estratégico Bolivia: {fecha_hoy_str}")
api_key = st.sidebar.text_input("API Key Gemini:", type="password")

st.header("1. Prensa y TV (Scraping Masivo)")
if api_key:
    genai.configure(api_key=api_key)
    if st.button("🚀 Iniciar Escaneo de Medios"):
        with st.spinner("Procesando noticias nacionales de las últimas 24h..."):
            datos = buscar_noticias()
            if datos:
                st.text_area("RESULTADOS:", value=procesar_ia(datos), height=600)
            else:
                st.warning("No se hallaron noticias relevantes en las últimas 24 horas.")

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
