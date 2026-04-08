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
            r = requests.get(f['u'], headers=headers, timeout=5) # Timeout más corto
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')

            for tag in soup.find_all(['a', 'h1', 'h2', 'h3']):
                texto = tag.get_text().strip()
                link = tag.get('href', '') if tag.name == 'a' else (tag.find('a').get('href', '') if tag.find('a') else '')
                t_low = texto.lower()
                
                # Filtro: Texto largo, no repetido y no en lista negra
                if len(texto) > 40 and t_low not in vistos_texto:
                    if not any(b in t_low for b in BLACKLIST):
                        full_link = link if link.startswith('http') else f['u'].rstrip('/') + "/" + link.lstrip('/')
                        hallazgos.append(f"MEDIO: {f['n']} | NOTICIA: {texto} | LINK: {full_link}")
                        vistos_texto.add(t_low)
        except: continue
    
    # IMPORTANTE: Retornamos solo las primeras 40 para que no sea infinito
    return hallazgos[:40]

# --- 3. PROCESAMIENTO IA ---
def procesar_ia_safe(datos, api_key):
    genai.configure(api_key=api_key)
    # Autodetectar modelo
    modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    modelo_id = next((m for m in modelos if "flash" in m), modelos[0])
    model = genai.GenerativeModel(modelo_id)
    
    reporte = ""
    barra = st.progress(0)
    
    # Procesar en lotes de 5 para ir rápido pero seguro
    for i in range(0, len(datos), 5):
        bloque = "\n".join(datos[i:i+5])
        prompt = f"RESUMEN NACIONAL BOLIVIA {fecha_hoy_str}. No deportes/farandula/internacional. FORMATO: *TITULAR*, MEDIO, RESUMEN 4-6 LÍNEAS, URL."
        
        try:
            res = model.generate_content(prompt + "\n\nDATOS:\n" + bloque)
            reporte += res.text + "\n\n---\n\n"
            time.sleep(2) # Pausa mínima
        except:
            time.sleep(5)
            continue
        
        barra.progress((i + 5) / len(datos) if (i + 5) < len(datos) else 1.0)
            
    return reporte

# --- 4. INTERFAZ ---
st.title(f"Monitor Nacional Bolivia: {fecha_hoy_str}")

with st.sidebar:
    api_key = st.text_input("Gemini API Key:", type="password")
    max_notas = st.slider("Cantidad de notas a procesar:", 10, 50, 25)

if st.button("🚀 Iniciar Escaneo Rápido"):
    if not api_key:
        st.error("Falta API Key")
    else:
        with st.spinner("Rastreando medios (esto será rápido)..."):
            # 1. Scraping
            todas = buscar_noticias_fast()
            seleccion = todas[:max_notas]
            
            if seleccion:
                st.success(f"Capturadas {len(todas)} noticias. Procesando las {len(seleccion)} mejores para evitar bloqueo.")
                
                # 2. Procesamiento IA
                resultado = procesar_ia_safe(seleccion, api_key)
                
                # 3. Mostrar Resultado
                st.subheader("Reporte Final")
                st.text_area("Copia el reporte aquí:", value=resultado, height=600)
            else:
                st.warning("No se hallaron noticias que pasen el filtro.")

st.divider()

# BLOQUE DE REDES
st.header("Búsqueda en Redes")
redes = ["Facebook", "X", "TikTok", "Instagram"]
cols = st.columns(4)
for idx, r in enumerate(redes):
    with cols[idx]:
        q = urllib.parse.quote(f'site:{r.lower()}.com "Bolivia" -deportes -fútbol')
        st.markdown(f"🔗 [Ver {r}](https://www.google.com/search?q={q}&tbs=qdr:d)")
