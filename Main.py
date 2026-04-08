import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import urllib.parse
import time

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Monitor Estratégico Bolivia", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# Filtros de búsqueda
KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "finanzas", "ministro", "economía", "aduana"]
BLACKLIST = ["deporte", "fútbol", "farandula", "show", "internacional", "entretenimiento"]

# --- 2. MOTOR DE BÚSQUEDA DE MEDIOS (NUEVO) ---
def obtener_noticias_bolivia():
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
    
    resultados_crudos = []
    enlaces_vistos = set()
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for fuente in fuentes:
        try:
            response = requests.get(fuente['url'], headers=headers, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscamos todos los enlaces que contengan texto
            for link in soup.find_all('a', href=True):
                texto = link.get_text().strip()
                href = link['href']
                
                # Validación de relevancia
                if len(texto) > 25 and any(k in texto.lower() for k in KEYWORDS):
                    if not any(b in texto.lower() for b in BLACKLIST):
                        if href not in enlaces_vistos:
                            full_url = href if href.startswith('http') else fuente['url'].rstrip('/') + "/" + href.lstrip('/')
                            resultados_crudos.append({
                                "medio": fuente['nombre'],
                                "titular": texto,
                                "url": full_url
                            })
                            enlaces_vistos.add(href)
        except:
            continue
            
    return resultados_crudos

# --- 3. PROCESAMIENTO CON IA (SIMPLIFICADO) ---
def procesar_con_ia(lista_noticias, api_key):
    if not lista_noticias:
        return "No se encontraron noticias con los filtros actuales."
    
    genai.configure(api_key=api_key)
    
    # Intentar detectar el modelo disponible automáticamente
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_id = next((m for m in modelos if "flash" in m), modelos[0])
        model = genai.GenerativeModel(modelo_id)
    except:
        return "Error al conectar con los modelos de Google. Verifica tu API Key."

    reporte_final = ""
    
    # Procesamos en grupos pequeños para evitar el error de cuota 429
    for i in range(0, len(lista_noticias), 3):
        grupo = lista_noticias[i:i+3]
        contexto = "\n".join([f"MEDIO: {n['medio']} | TITULAR: {n['titular']} | LINK: {n['url']}" for n in grupo])
        
        prompt = f"""
        Actúa como un analista político en Bolivia. Fecha: {fecha_hoy}.
        Para cada noticia en los DATOS, genera el siguiente formato:
        
        *TITULAR EN MAYÚSCULAS*
        MEDIO EN MAYÚSCULAS
        Redacta un resumen de 4 a 6 líneas sobre la importancia económica o fiscal de esta noticia en Bolivia.
        URL (del dato original)
        ---
        DATOS:
        {contexto}
        """
        
        try:
            response = model.generate_content(prompt)
            reporte_final += response.text + "\n\n"
            time.sleep(2) # Pausa para respetar la cuota
        except Exception as e:
            if "429" in str(e):
                st.error("Límite de cuota alcanzado. Esperando...")
                time.sleep(10)
            else:
                reporte_final += f"\n(Error al procesar bloque: {str(e)})\n"
                
    return reporte_final

# --- 4. INTERFAZ DE USUARIO ---
st.title(f"Monitor Estratégico Bolivia | {fecha_hoy}")

with st.sidebar:
    st.header("Configuración")
    key = st.text_input("Gemini API Key:", type="password")
    st.info("Este monitor rastrea noticias fiscales y económicas en los principales medios nacionales.")

st.header("1. Prensa y TV (Nacional)")

if st.button("🔍 Iniciar Monitoreo"):
    if not key:
        st.error("Por favor, introduce tu API Key.")
    else:
        with st.spinner("Rastreando medios bolivianos..."):
            noticias = obtener_noticias_bolivia()
            
            if noticias:
                st.success(f"Se encontraron {len(noticias)} noticias potenciales.")
                resultado = procesar_con_ia(noticias, key)
                st.text_area("REPORTE GENERADO:", value=resultado, height=500)
            else:
                st.warning("No se hallaron noticias que coincidan con los filtros de hoy.")

st.divider()

# --- 5. BLOQUE DE REDES SOCIALES (CONSERVADO) ---
st.header("2. Pulso en Redes Sociales")
redes = ["Facebook", "X", "TikTok", "Instagram", "Threads"]
col1, col2 = st.columns(2)

with col1:
    st.subheader("Últimas 24 Horas")
    for r in redes:
        query = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"🔗 [Buscar en {r} (24h)](https://www.google.com/search?q={query}&tbs=qdr:d)")

with col2:
    st.subheader("Última Hora")
    for r in redes:
        query = urllib.parse.quote(f'site:{r.lower()}.com "impuestos" "Bolivia"')
        st.markdown(f"🔗 [Buscar en {r} (1h)](https://www.google.com/search?q={query}&tbs=qdr:h)")
