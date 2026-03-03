import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")

# --- LÓGICA DE TIEMPO BOLIVIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_ref = ahora.strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO DE NOTICIAS: {fecha_ref}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_hora_url(url):
    """Busca patrones de hora HHMM o HH-MM en la URL."""
    # Caso Red Uno y otros (patrones de 4 dígitos al final de la fecha)
    match = re.search(r'202[4-6]\d{2,4}(\d{2})(\d{2})', url)
    if match:
        return f"{match.group(1)}:{match.group(2)}"
    return None

def extraer_noticias():
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
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    data_raw = ""
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=12)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Buscamos artículos
            articulos = soup.find_all(['h1', 'h2', 'h3', 'article'], limit=20)
            
            for art in articulos:
                titulo = art.get_text().strip()
                a_tag = art.find('a') if art.name != 'a' else art
                if not a_tag: a_tag = art.find_parent('a')
                
                if a_tag and a_tag.get('href') and len(titulo) > 30:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'].rstrip('/') + link
                    
                    # --- EXTRACCIÓN DE HORA MULTINIVEL ---
                    # 1. Buscar etiquetas HTML de tiempo cerca del título
                    info_tiempo = ""
                    contenedor = art.parent
                    tag_t = contenedor.find(['time', 'span', 'div'], class_=re.compile(r'time|date|hora|fecha|entry-meta', re.I))
                    if tag_t:
                        info_tiempo = tag_t.get_text().strip()
                    
                    # 2. Buscar en la URL (Red Uno style)
                    if not info_tiempo:
                        info_tiempo = extraer_hora_url(full_link)
                    
                    # 3. Metadatos específicos del artículo (si están en la home)
                    if not info_tiempo:
                        meta_t = art.find_next("meta", property="article:published_time")
                        if meta_t: info_tiempo = meta_t.get("content", "")

                    data_raw += f"MEDIO: {fuente['nombre']} | DATO_TIEMPO: {info_tiempo} | TEMA: {titulo} | LINK: {full_link}\n"
        except: continue
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
                    status_ia.text(f"⚖️ Analizando noticias del día...")
                    model = genai.GenerativeModel(modelo_valido)
                    
                    prompt = f"""
                    HOY ES: {fecha_ref}. HORA ACTUAL EN BOLIVIA: {ahora.strftime('%H:%M')}.
                    
                    INSTRUCCIONES CRÍTICAS PARA LA HORA:
                    1. Revisa el campo 'DATO_TIEMPO'. Si contiene una hora (ej. 10:59, 13:10), esa es la HORA REAL. ÚSALA.
                    2. Si 'DATO_TIEMPO' está vacío, busca la hora en el texto del 'LINK'.
                    3. Si después de buscar no hay rastro, pon una hora estimada lógica de hoy (antes de las {ahora.strftime('%H:%M')}) seguida de "(aprox.)".
                    4. IMPORTANTE: No inventes la hora 15:30 para todo. Si la noticia parece antigua o de la mañana, estima una hora matutina.

                    ORDEN DE SALIDA:
                    *TITULAR EN MAYÚSCULAS Y NEGRITA*
                    MEDIO EN MAYÚSCULAS Y NEGRITA
                    HH:MM (Solo la hora)
                    Párrafo informativo (4 a 6 líneas).
                    URL

                    DATOS DE ENTRADA:
                    {noticias_raw}
                    """
                    
                    response = model.generate_content(prompt)
                    status_ia.empty()
                    
                    if response.text:
                        st.subheader("📋 Resultado (Times New Roman 10):")
                        processed_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', response.text)
                        html_content = processed_text.replace("\n", "<br>")
                        
                        styled_html = f"""
                        <div style="font-family: 'Times New Roman', serif; font-size: 13.3px; color: black; background-color: white; padding: 25px; border: 1px solid #ccc; line-height: 1.3; text-align: justify;">
                            {html_content}
                        </div>
                        """
                        st.markdown(styled_html, unsafe_allow_html=True)
                        st.success("Monitoreo generado.")
                except Exception as e:
                    st.error(f"Error: {e}")
