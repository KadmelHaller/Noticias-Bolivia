import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
from urllib.parse import urlparse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor Tributario 24h", page_icon="🇧🇴", layout="wide")

zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# Palabras clave simplificadas para ampliar el alcance
KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "aduana", "econom", "dolar", "recauda"]

def es_valido(texto, url):
    txt = (texto + url).lower()
    return any(k in txt for k in KEYWORDS)

st.title(f"🔍 RELEVAMIENTO TRIBUTARIO 24H: {fecha_hoy}")
api_key = st.sidebar.text_input("Gemini API Key:", type="password")

def obtener_datos():
    # 1. LISTA DE MEDIOS (PORTADAS PRINCIPALES PARA NO PERDER NADA)
    medios = [
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "r": "Cochabamba", "t": "Escrito"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba", "t": "Escrito"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "r": "Santa Cruz", "t": "Escrito"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "r": "Santa Cruz", "t": "Escrito"},
        {"n": "UNITEL", "u": "https://unitel.bo/", "r": "Nacional", "t": "TV"},
        {"n": "RED UNO", "u": "https://www.reduno.com.bo/", "r": "Nacional", "t": "TV"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/", "r": "Nacional", "t": "Digital"},
        # 2. BÚSQUEDA DIRECTA EN GOOGLE PARA RRSS (Como pediste)
        {"n": "FACEBOOK CBBA", "u": "https://www.google.com/search?q=%22impuestos%22+%22Cochabamba%22+site:facebook.com", "r": "Cochabamba", "t": "RRSS"},
        {"n": "RRSS SCZ", "u": "https://www.google.com/search?q=%22impuestos%22+%22Santa+Cruz%22+(site:x.com+OR+site:instagram.com+OR+site:tiktok.com)", "r": "Santa Cruz", "t": "RRSS"}
    ]

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    recopilacion = ""
    progress = st.progress(0)

    for idx, m in enumerate(medios):
        st.write(f"📡 Revisando {m['n']}...")
        progress.progress((idx + 1) / len(medios))
        try:
            # Aumentamos el timeout para no perder medios lentos
            r = requests.get(m['u'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Buscamos TODOS los enlaces
            links = soup.find_all('a', href=True)
            encontrados = 0
            
            for l in links:
                url = l['href']
                if not url.startswith('http'):
                    base = urlparse(m['u']).scheme + "://" + urlparse(m['u']).netloc
                    url = base + "/" + url.lstrip('/')
                
                titulo = l.get_text().strip()
                
                # Si es RRSS o si el título/URL es relevante, lo guardamos
                if (m['t'] == "RRSS" and "google.com" not in url) or (len(titulo) > 20 and es_valido(titulo, url)):
                    recopilacion += f"REGIÓN: {m['r']} | MEDIO: {m['n']} | TIPO: {m['t']} | TÍTULO: {titulo} | LINK: {url}\n\n"
                    encontrados += 1
                
                if encontrados > 15: break # Limite por medio para no saturar
        except:
            st.warning(f"⚠️ No se pudo acceder a {m['n']}")
            
    return recopilacion

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 INICIAR RELEVAMIENTO COMPLETO'):
        with st.status("Escaneando la red boliviana...") as status:
            datos_brutos = obtener_datos()
            
            if len(datos_brutos) > 100:
                status.update(label="Analizando hallazgos con IA...", state="running")
                try:
                    # Usamos el motor más flexible para evitar el error 404
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = f"""
                    Hoy es {fecha_hoy}. Actúa como un Analista de Prensa especializado en Economía.
                    Tu objetivo es listar TODAS las noticias relevantes sobre IMPUESTOS detectadas.
                    
                    REGLAS:
                    1. Si la noticia menciona 'Impuestos Municipales' o 'Nacionales', cámbialo a 'IMPUESTOS'.
                    2. Divide el reporte en: 1. COCHABAMBA y 2. SANTA CRUZ.
                    3. Dentro de cada ciudad, agrupa por: Escritos, TV, Digitales y Redes Sociales.
                    4. Para cada noticia: TÍTULO (MAYUS), MEDIO (MAYUS), resumen de 4 líneas y LINK.
                    5. Si encuentras duplicados, combínalos en una sola entrada mencionando los medios.
                    """
                    
                    respuesta = model.generate_content(prompt + "\n\nDATOS RECOPILADOS:\n" + datos_brutos)
                    
                    status.update(label="Reporte Generado", state="complete")
                    
                    # Formateo estético para el reporte
                    texto_final = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', respuesta.text)
                    st.markdown(f'''
                    <div style="background-color: white; color: black; padding: 30px; border: 1px solid #ccc; font-family: 'Times New Roman', serif; text-align: justify; line-height: 1.6;">
                        <h2 style="text-align: center;">REPORTE DIARIO DE IMPUESTOS</h2>
                        <hr>
                        {texto_final.replace("\n", "<br>")}
                    </div>
                    ''', unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Error de IA: {e}. Intenta usar el modelo 'gemini-pro' si persiste.")
            else:
                st.error("No se capturaron suficientes datos. Revisa la conexión a internet.")
