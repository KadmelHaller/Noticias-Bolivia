import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import time
import re

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")

# --- LÓGICA DE TIEMPO BOLIVIA (SIEMPRE HOY) ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_ref = ahora.strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO DE NOTICIAS: {fecha_ref}")
st.info(f"Buscando noticias publicadas hoy: {fecha_ref}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_noticias():
    # Lista de fuentes desde portadas principales
    fuentes = [
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/", "base": "https://www.opinion.com.bo"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/", "base": "https://www.lostiempos.com"},
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/", "base": "https://lavozdetarija.com"},
        {"nombre": "UNITEL", "url": "https://unitel.bo/", "base": "https://unitel.bo"},
        {"nombre": "RED UNO", "url": "https://www.reduno.com.bo/", "base": "https://www.reduno.com.bo"},
        {"nombre": "ATB", "url": "https://www.atb.com.bo/", "base": "https://www.atb.com.bo"},
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/", "base": "https://www.boliviatv.bo"},
        {"nombre": "BOLIVISION", "url": "https://www.redbolivision.tv.bo/", "base": "https://www.redbolivision.tv.bo"},
        {"nombre": "CADENA A", "url": "https://www.cadenaa.tv/", "base": "https://www.cadenaa.tv"},
        {"nombre": "URGENTE BO", "url": "https://www.urgente.bo/", "base": "https://www.urgente.bo"},
        {"nombre": "IN NOTICIAS", "url": "https://innoticiasbo.com/", "base": "https://innoticiasbo.com"},
        {"nombre": "ENFOQUE NEWS", "url": "https://enfoquenews.com.bo/", "base": "https://enfoquenews.com.bo"}
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    data_raw = ""
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=12)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')

            # Escaneo de titulares y metadatos básicos
            articulos = soup.find_all(['h1', 'h2', 'h3'], limit=15)
            
            for art in articulos:
                titulo = art.get_text().strip()
                a_tag = art.find('a') or art.find_parent('a')
                
                if a_tag and a_tag.get('href') and len(titulo) > 30:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'].rstrip('/') + link
                    
                    # Captura de hora visual o metadato de la etiqueta cercana
                    parent_text = art.parent.get_text()[:150].replace('\n', ' ')
                    
                    data_raw += f"SITIO_ORIGEN: {fuente['nombre']} | TEXTO_CERCANO: {parent_text} | TEMA: {titulo} | LINK: {full_link}\n"
        except:
            continue
            
    pb.empty()
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    
    if st.button('🚀 GENERAR MONITOREO'):
        modelo_valido = None
        try:
            modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            modelo_valido = next((m for m in modelos if "1.5-flash" in m), modelos[0])
        except: pass

        if modelo_valido:
            noticias_raw = extraer_noticias()
            if len(noticias_raw) > 300:
                status_ia = st.empty()
                try:
                    status_ia.text(f"⚖️ IA procesando noticias del {fecha_ref}...")
                    model = genai.GenerativeModel(modelo_valido)
                    
                    prompt = f"""
                    FECHA ACTUAL: {fecha_ref}.
                    HORA ACTUAL: {ahora.strftime('%H:%M')}.
                    
                    TAREA: Resumen técnico informativo para monitoreo de prensa.
                    
                    INSTRUCCIONES DE FILTRADO:
                    - Solo incluye noticias publicadas HOY {fecha_ref}.
                    - Prioridad: Economía, Impuestos, Gobierno
                    - Prioridad geográfica: Cochabamba y Tarija.
                    - Ignora deportes, farándula y notas internacionales.
                    - Orden de presentación: mismo orden estricto que de consulta.
                    
                    INSTRUCCIONES DE FORMATO (ESTRICTO):
                    - *TITULAR EN MAYÚSCULAS Y NEGRITA* (Un asterisco al inicio y otro al final).
                    - MEDIO EN MAYÚSCULAS Y NEGRITA (Debe coincidir con el SITIO_ORIGEN indicado).
                    - HORA: Si encuentras la hora exacta en la entrada, pon HH:MM. Si no la encuentras, deduce una hora lógica de hoy (antes de las {ahora.strftime('%H:%M')}) y añade al lado el texto "(aprox.)".
                    - Párrafo informativo: Entre 4 y 6 líneas.
                    - URL: Debe ser la URL real proporcionada en la entrada para ese titular.
                    
                    DATOS DE ENTRADA:
                    {noticias_raw}
                    """
                    
                    response = model.generate_content(prompt)
                    status_ia.empty()
                    
                    if response.text:
                        st.subheader("📋 Formato Times New Roman 10:")
                        
                        # Convertir negritas de Markdown a HTML
                        processed_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', response.text)
                        html_content = processed_text.replace("\n", "<br>")
                        
                        styled_html = f"""
                        <div style="
                            font-family: 'Times New Roman', Times, serif; 
                            font-size: 13.3px; 
                            color: black; 
                            background-color: white; 
                            padding: 25px; 
                            border: 1px solid #ccc;
                            line-height: 1.3;
                            text-align: justify;
                        ">
                            {html_content}
                        </div>
                        """
                        st.markdown(styled_html, unsafe_allow_html=True)
                        st.success("Monitoreo diario generado.")
                except Exception as e:
                    st.error(f"Error en la IA: {e}")
            else:
                st.error("No se pudo obtener información de las portadas. Intenta de nuevo.")
