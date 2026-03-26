import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import os
from urllib.parse import urlparse, parse_qs

st.set_page_config(page_title="Monitoreo Bolivia Pro", page_icon="🇧🇴", layout="wide")

# --- CONFIGURACIÓN DE TIEMPO Y FILTROS ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')
HISTORIAL_FILE = "vistos_monitoreo.txt"

# Palabras clave para asegurar relevancia técnica en medios escritos
TEMAS_OK = ["impuesto", "sin", "tributario", "factura", "economía", "gobierno", "arce", "dólar", "clausura", "fiscalización", "aduana", "subsidio", "gasolina", "diésel", "presupuesto"]

# --- FUNCIONES DE PERSISTENCIA ---
def gestionar_historial():
    if os.path.exists(HISTORIAL_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(HISTORIAL_FILE), zona_horaria)
        # Si la ejecución es en menos de 1 hora, permitimos repetir para revisión de calidad
        if (ahora - mtime).total_seconds() < 3600: return set()
        with open(HISTORIAL_FILE, "r") as f: return set(f.read().splitlines())
    return set()

def guardar_historial(url):
    with open(HISTORIAL_FILE, "a") as f: f.write(url + "\n")

# --- FUNCIONES DE LIMPIEZA Y FILTRADO ---
def limpiar_url_google(url_google):
    """Extrae la URL real de un enlace de resultado de Google"""
    if "google.com/url" not in url_google: return url_google
    parsed = urlparse(url_google)
    res = parse_qs(parsed.query).get('q')
    return res[0] if res else url_google

def es_relevante_y_actual(texto, url):
    txt = texto.lower()
    # Filtro estricto de años anteriores
    if any(old in txt for old in ["2021", "2022", "2023"]): return False
    # Validación de temas prioritarios
    return any(t in txt for t in TEMAS_OK) or any(t in url.lower() for t in TEMAS_OK)

# --- INICIO DE INTERFAZ ---
st.title(f"📰 MONITOREO ESTRATÉGICO: {fecha_hoy_bonita}")
st.markdown("### Enfoque: Impuestos, Economía y Gobierno")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}

# --- FUNCIÓN 1: SCRAPING DE MEDIOS ESCRITOS, TV Y DIGITALES ---
def procesar_medios(historial):
    fuentes = [
        # --- COCHABAMBA ---
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "t": "Escrito", "r": "Cochabamba"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/seccion/cochabamba/", "t": "Escrito", "r": "Cochabamba"},
        
        # --- SANTA CRUZ ---
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/economia", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/category/economia/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "LA ESTRELLA", "u": "https://www.laestrelladeloriente.com/category/nacional/", "t": "Escrito", "r": "Santa Cruz"},
        
        # --- TV Y DIGITALES (NACIONAL) ---
        {"n": "UNITEL", "u": "https://unitel.bo/noticias/economia", "t": "TV", "r": "Nacional"},
        {"n": "RED UNO", "u": "https://www.reduno.com.bo/noticias", "t": "TV", "r": "Nacional"},
        {"n": "ATB", "u": "https://www.atb.com.bo/seccion/economia", "t": "TV", "r": "Nacional"},
        {"n": "BOLIVIA TV", "u": "https://www.boliviatv.bo/noticias", "t": "TV", "r": "Nacional"},
        {"n": "BOLIVISION", "u": "https://www.redbolivision.tv.bo/noticias/", "t": "TV", "r": "Nacional"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/economia", "t": "Digital", "r": "Nacional"},
        {"n": "IN NOTICIAS", "u": "https://innoticiasbo.com/", "t": "Digital", "r": "Nacional"},
        {"n": "ENFOQUE NEWS", "u": "https://enfoquenews.com.bo/", "t": "Digital", "r": "Nacional"}
    ]
    
    data_final = ""
    st.write("---")
    st.subheader("📡 Escaneando Medios de Comunicación...")
    pb = st.progress(0)
    
    for i, f in enumerate(fuentes):
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            vistos = 0
            
            for l in links:
                url = l['href']
                if not url.startswith('http'): 
                    base = urlparse(f['u']).scheme + "://" + urlparse(f['u']).netloc
                    url = base + "/" + url.lstrip('/')
                
                if url in historial: continue
                
                # Filtro de profundidad para evitar URLs de portadas/secciones
                if url.count('/') < 4: continue
                
                titulo = l.get_text().strip()
                if len(titulo) < 25: continue

                if es_relevante_y_actual(titulo, url):
                    try:
                        rn = requests.get(url, headers=headers, timeout=8)
                        s_n = BeautifulSoup(rn.text, 'html.parser')
                        parrafos = s_n.find_all('p', limit=5)
                        txt = " ".join([p.get_text().strip() for p in parrafos if len(p.get_text()) > 30])
                        
                        if len(txt) > 100 and not any(año in txt for año in ["2021", "2022", "2023"]):
                            data_final += f"REGION: {f['r']} | TIPO: {f['t']} | MEDIO: {f['n']} | TITULAR: {titulo} | TXT: {txt[:800]} | LINK: {url}\n\n"
                            guardar_historial(url)
                            vistos += 1
                    except: continue
                if vistos >= 4: break # Límite por fuente
        except: continue
    return data_final

# --- FUNCIÓN 2: BUSQUEDA ESPECIALIZADA EN RRSS (INFLUENCERS) ---
def procesar_rrss(historial, model):
    st.write("---")
    st.subheader("🕵️‍♂️ Buscando Influencers en Redes Sociales (Últimas 12 Horas)...")
    pb_rrss = st.progress(0)
    
    plataformas = [
        {"n": "Facebook", "s": "site:facebook.com"},
        {"n": "TikTok", "s": "site:tiktok.com"},
        {"n": "X (Twitter)", "s": "site:x.com"},
        {"n": "Instagram", "s": "site:instagram.com"}
    ]
    regiones = ["Cochabamba", "Santa Cruz"]
    
    rrss_raw_data = ""
    # Total búsquedas = 4 plataformas * 2 regiones = 8
    total_busquedas = len(plataformas) * len(regiones)
    contador = 0
    
    for region in regiones:
        for plat in plataformas:
            contador += 1
            pb_rrss.progress(contador / total_busquedas)
            
            # FORMATO EXACTO SOLICITADO: "impuestos" "Region" site:plataforma.com
            # Añadimos &tbs=qdr:h12 para filtrar por últimas 12 horas en Google
            query = f'\"impuestos\" \"{region}\" {plat["s"]}'
            url_search = f"https://www.google.com/search?q={query}&tbs=qdr:h12"
            
            try:
                r = requests.get(url_search, headers=headers, timeout=15)
                soup = BeautifulSoup(r.text, 'html.parser')
                # En Google search, los resultados suelen estar en divs class "g"
                resultados = soup.find_all('div', class_='g')
                vistos_rrss = 0
                
                for res in resultados:
                    link_tag = res.find('a', href=True)
                    if not link_tag: continue
                    
                    url_google = link_tag['href']
                    url_final = limpiar_url_google(url_google)
                    
                    # Verificaciones básicas de URL
                    if url_final in historial or plat['n'].lower() not in url_final.lower(): continue
                    if any(x in url_final for x in ['google.com/search', 'accounts.google']): continue
                    
                    # Capturar el título y el snippet (pequeño resumen) que da Google
                    title_tag = res.find('h3')
                    snippet_tag = res.find('div', class_='VwiC3b') # Clase común para snippets
                    
                    if title_tag and snippet_tag:
                        rrss_raw_data += f"REGION: {region} | PLATAFORMA: {plat['n']} | TITULO_POST: {title_tag.get_text()} | SNIPPET: {snippet_tag.get_text()} | LINK: {url_final}\n\n"
                        guardar_historial(url_final)
                        vistos_rrss += 1
                    
                    if vistos_rrss >= 5: break # Límite por búsqueda (5 posts por plataforma/región)
            except: continue
            
    # --- PROMPT 2: FILTRADO Y RESUMEN DE INFLUENCERS CON GEMINI ---
    if len(rrss_raw_data) > 150:
        st.write("🧠 Gemini está filtrando y resumiendo a los influencers...")
        prompt_rrss = """
        Eres un analista experto en política y economía boliviana. Te proporciono una lista cruda de publicaciones de redes sociales encontradas en Google.
        
        TUS TAREAS ESENCIALES:
        1.  **FILTRAR MEDIOS DE COMUNICACIÓN:** Elimina CUALQUIER publicación hecha por cuentas oficiales de periódicos (ej: El Deber, Los Tiempos, Opinión), canales de TV (ej: Unitel, Red Uno, ATB) o portales de noticias institucionalizados.
        2.  **IDENTIFICAR INFLUENCERS:** Solo mantén publicaciones de personas individuales (analistas, economistas, políticos, líderes de opinión, ciudadanos influyentes) de Bolivia.
        3.  **VERIFICAR TEMA:** Asegúrate de que el post trate sobre IMPUESTOS (denuncias de clausuras, análisis tributario, opinión sobre SIN, etc.).
        
        FORMATO DE SALIDA (Para cada influencer aceptado):
        **TITULAR DEL POST O RESUMEN CORTO**
        **[PLATAFORMA] - NOMBRE DEL INFLUENCER (Si es identificable, sino 'Influencer Político/Económico')**
        Resumen técnico y de opinión del post (4-6 líneas).
        URL directo

        Separa los resultados por REGIÓN (Cochabamba y Santa Cruz). Si no hay influencers aceptados para una región o plataforma, simplemente no muestres esa sección.
        """
        try:
            response = model.generate_content([prompt_rrss, rrss_raw_data])
            return response.text
        except:
            return "Error procesando el resumen de RRSS."
    return ""

# --- EJECUCIÓN PRINCIPAL ---
if api_key:
    genai.configure(api_key=api_key)
    # Inicializar modelo una sola vez
    model = genai.GenerativeModel('models/gemini-flash-latest')
    
    if st.button('🚀 GENERAR REPORTE INTEGRAL'):
        historial = gestionar_historial()
        
        # 1. Obtener y procesar medios tradicionales
        raw_medios = procesar_medios(historial)
        
        # 2. Obtener y procesar RRSS (Influencers) con filtro de Gemini integrado
        reporte_rrss = procesar_rrss(historial, model)
        
        # --- PROMPT 3: GEMINI UNIFICA Y GENERA EL REPORTE FINAL ---
        st.write("---")
        st.subheader("📋 Unificando y Formateando Reporte Final...")
        
        # Construir el input
