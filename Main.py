import streamlit as st
import google.generativeai as genai
import feedparser  # Instalación: pip install feedparser
from datetime import datetime
import pytz
import urllib.parse
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor Nacional Bolivia", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy_str = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# --- 2. MOTOR DE CAPTURA (GOOGLE ALERTS RSS) ---
def buscar_noticias_alerts(rss_url):
    feed = feedparser.parse(rss_url)
    hallazgos = []
    
    for entry in feed.entries:
        # Extraer el título y limpiar el link de redirección de Google
        titulo = entry.title
        link_crudo = entry.link
        
        # Limpieza básica de la URL de Google Alerts
        if "url?q=" in link_crudo:
            link_limpio = link_crudo.split("url?q=")[1].split("&")[0]
        else:
            link_limpio = link_crudo
            
        hallazgos.append({
            "titular": titulo,
            "link": link_limpio
        })
    
    return hallazgos

# --- 3. ANALISTA IA ---
def procesar_ia_alerts(datos, api_key):
    genai.configure(api_key=api_key)
    modelos_visibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    modelo_id = next((m for m in modelos_visibles if "flash" in m), modelos_visibles[0])
    model = genai.GenerativeModel(modelo_id)
    
    reporte = ""
    # Procesamiento por lotes de 5 notas
    for i in range(0, len(datos), 5):
        lote = datos[i:i+5]
        bloque_texto = "\n".join([f"NOTICIA: {n['titular']} | LINK: {n['link']}" for n in lote])
        
        prompt = f"""
        FECHA: {fecha_hoy_str}. Reporte nacional de BOLIVIA sobre IMPUESTOS y ECONOMÍA.
        INSTRUCCIÓN: Procesa cada noticia individualmente.
        FORMATO POR NOTICIA:
        *TITULAR EXACTO EN MAYÚSCULAS*
        MEDIO EN MAYÚSCULAS (Si es identificable por la URL)
        Resumen de 4 a 6 líneas sobre la relevancia económica o fiscal en el contexto boliviano.
        URL
        ---
        """
        try:
            res = model.generate_content(prompt + "\n\nDATOS:\n" + bloque_texto)
            reporte += res.text + "\n\n"
            time.sleep(2) # Respetar cuota gratuita
        except:
            continue
            
    return reporte

# --- 4. INTERFAZ ---
st.title(f"Monitor Estratégico Bolivia: {fecha_hoy_str}")
st.caption("Configuración: Búsqueda 'Impuestos' y 'Economía' vía Google Alerts (RSS)")

with st.sidebar:
    api_key = st.text_input("API Key Gemini:", type="password")
    rss_url = st.text_input("URL del Feed RSS (Google Alerts):")

if st.button("🚀 Iniciar Escaneo"):
    if not api_key or not rss_url:
        st.error("Por favor ingresa la API Key (AIzaSyCgkJXW9znhE-TLiHCOxIW0Kv_ruqrFK_E) y la URL del Feed RSS. (https://www.google.com.bo/alerts/feeds/09233459801766163520/10520035271565045257)")
    else:
        with st.spinner("Procesando alertas de Google..."):
            noticias = buscar_noticias_alerts(rss_url)
            if noticias:
                resultado = procesar_ia_alerts(noticias, api_key)
                st.text_area("RESULTADOS:", value=resultado, height=600)
            else:
                st.warning("No se encontraron nuevas entradas en el feed de alertas.")

st.divider()

# --- 5. REDES SOCIALES (FORMATO ORIGINAL SOLICITADO) ---
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
