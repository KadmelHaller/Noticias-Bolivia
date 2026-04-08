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
        {"n": "UNITEL", "u": "https://unitel.bo/"},
        {"n": "BOLIVIA TV", "u": "https://www.boliviatv.bo/"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/"},
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
                
                if len(texto) > 30 and any(k in texto_lower for k in KEYWORDS):
                    if not any(b in texto_lower for b in BLACKLIST_TOPICS):
                        if link and link not in enlaces_vistos:
                            full_link = link if link.startswith('http') else f['u'].rstrip('/') + "/" + link.lstrip('/')
                            lista_noticias.append(f"MEDIO: {f['n']} | NOTICIA: {texto} | LINK: {full_link}")
                            enlaces_vistos.add(link)
        except: continue
    return lista_noticias

# --- 3. ANALISTA IA (DETECCIÓN AUTOMÁTICA DE MODELO Y LOTES) ---
def procesar_ia_lotes(lista_noticias):
    if not lista_noticias: return "No se hallaron noticias."
    
    try:
        # DETECCIÓN DINÁMICA: Buscamos qué modelo acepta tu API
        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Prioridad 1: gemini-1.5-flash | Prioridad 2: gemini-pro | Prioridad 3: el primero que sirva
        modelo_final = next((m for m in modelos_disponibles if "1.5-flash" in m), 
                            next((m for m in modelos_disponibles if "pro" in m), modelos_disponibles[0]))
        
        model = genai.GenerativeModel(modelo_final)
        resultado_final = ""
        lotes = [lista_noticias[i:i + 3] for i in range(0, len(lista_noticias), 3)]
        
        progreso = st.progress(0)
        for idx, lote in enumerate(lotes):
            datos_bloque = "\n".join(lote)
            prompt = f"FECHA: {fecha_hoy_str}. Reporte nacional BOLIVIA. NO AGRUPES. Procesa cada noticia individualmente. FORMATO: *TITULAR EN MAYÚSCULAS*, MEDIO EN MAYÚSCULAS, Contenido de 4 a 6 líneas, URL."
            
            for intento in range(3):
                try:
                    res = model.generate_content(prompt + "\n\nDATOS:\n" + datos_bloque)
                    resultado_final += res.text + "\n\n"
                    break
                except Exception as e:
                    if "429" in str(e): # Error de Cuota
                        time.sleep(12)
                    else: 
                        resultado_final += f"Error en lote: {str(e)}\n"
                        break
            
            progreso.progress((idx + 1) / len(lotes))
            time.sleep(2)
            
        return resultado_final
    except Exception as e:
        return f"Error crítico al detectar modelo: {str(e)}"

# --- 4. INTERFAZ ---
st.title(f"Monitor Estratégico Bolivia: {fecha_hoy_str}")
api_key = st.sidebar.text_input("API Key Gemini:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    if st.button("🚀 Iniciar Escaneo"):
        with st.spinner("Detectando modelo y procesando noticias..."):
            noticias_crudas = buscar_noticias()
            if noticias_crudas:
                resultado = procesar_ia_lotes(noticias_crudas)
                st.text_area("RESULTADOS:", value=resultado, height=600)
            else:
                st.warning("No se hallaron noticias con los filtros actuales.")
else:
    st.info("Introduce tu API Key en el menú lateral.")

st.divider()

# REDES SOCIALES (NACIONAL)
redes = ["Facebook", "X", "TikTok", "Instagram", "Threads"]
c1, c2 = st.columns(2)
with c1:
    st.header("2. Redes Sociales (24h)")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"🔗 [Ver {r} (24h)](https://www.google.com/search?q={q}&tbs=qdr:d)")
with c2:
    st.header("3. Redes Sociales (1h)")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"🔗 [Ver {r} (1h)](https://www.google.com/search?q={q}&tbs=qdr:h)")
