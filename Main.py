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
                
                if len(texto) > 30 and any(k in texto_lower for k in KEYWORDS):
                    if not any(b in texto_lower for b in BLACKLIST_TOPICS):
                        if link and link not in enlaces_vistos:
                            full_link = link if link.startswith('http') else f['u'].rstrip('/') + "/" + link.lstrip('/')
                            lista_noticias.append(f"MEDIO: {f['n']} | NOTICIA: {texto} | LINK: {full_link}")
                            enlaces_vistos.add(link)
        except: continue
    return lista_noticias

# --- 3. ANALISTA IA (CON MANEJO DE CUOTA REFORZADO) ---
def procesar_ia_lotes(lista_noticias):
    if not lista_noticias: return "No se hallaron datos crudos."
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash") # Usamos Flash 1.5 que es el más estable en cuota
        
        resultado_final = ""
        # Procesamos de 3 en 3 para no saturar la cuota diaria
        lotes = [lista_noticias[i:i + 3] for i in range(0, len(lista_noticias), 3)]
        
        progreso = st.progress(0)
        for idx, lote in enumerate(lotes):
            datos_bloque = "\n".join(lote)
            prompt = f"""
            FECHA: {fecha_hoy_str}. Reporte nacional BOLIVIA. 
            NO AGRUPES. Procesa cada noticia individualmente.
            FORMATO:
            *TITULAR EN MAYÚSCULAS*
            MEDIO EN MAYÚSCULAS
            Extrae de forma coherente el contenido: 4 a 6 líneas de texto continuo.
            URL (sin etiquetas)
            ---
            """
            
            # Reintento en caso de error 429
            exito = False
            for intento in range(3):
                try:
                    res = model.generate_content(prompt + "\n\nDATOS:\n" + datos_bloque)
                    resultado_final += res.text + "\n\n"
                    exito = True
                    break
                except Exception as e:
                    if "429" in str(e):
                        time.sleep(10) # Espera técnica para liberar cuota
                    else:
                        resultado_final += f"\nError en lote: {str(e)}\n"
                        break
            
            progreso.progress((idx + 1) / len(lotes))
            time.sleep(2) # Pausa entre llamadas para no ser detectado como bot masivo
            
        return resultado_final
    except Exception as e:
        return f"Error crítico: {str(e)}"

# --- 4. INTERFAZ ---
st.title(f"Monitor Estratégico Bolivia: {fecha_hoy_str}")
api_key = st.sidebar.text_input("API Key Gemini:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    if st.button("🚀 Iniciar Escaneo"):
        with st.spinner("Escaneando medios y procesando por lotes..."):
            noticias_crudas = buscar_noticias()
            if noticias_crudas:
                resultado = procesar_ia_lotes(noticias_crudas)
                st.text_area("RESULTADOS:", value=resultado, height=600)
            else:
                st.warning("No hay noticias hoy con esas palabras clave.")
else:
    st.info("Introduce tu API Key.")

st.divider()

# REDES SOCIALES
redes = ["Facebook", "X", "TikTok", "Instagram", "Threads"]
col1, col2 = st.columns(2)

with col1:
    st.header("2. Redes Sociales (24h)")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"🔗 [Ver en {r}](https://www.google.com/search?q={q}&tbs=qdr:d)")

with col2:
    st.header("3. Redes Sociales (1h)")
    for r in redes:
        q = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"🔗 [Ver en {r}](https://www.google.com/search?q={q}&tbs=qdr:h)")
