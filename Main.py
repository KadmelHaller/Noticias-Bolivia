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
st.info(f"Prioridad de hora: Texto del artículo > URL > Metadatos")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_hora_url(url):
    # Patrón: busca 4 dígitos de hora después de una fecha 2024-2026
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
            
            # Meta global (Nivel 3)
            meta_global = soup.find("meta", property="article:published_time")
            meta_txt = meta_global.get("content", "") if meta_global else ""

            articulos = soup.find_all(['h1', 'h2', 'h3'], limit=15)
            
            for art in articulos:
                titulo = art.get_text().strip()
                a_tag = art.find('a') or art.find_parent('a')
                
                if a_tag and a_tag.get('href') and len(titulo) > 30:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'].rstrip('/') + link
                    
                    # --- JERARQUÍA DE HORA ---
                    hora_encontrada = ""
                    
                    # 1. Buscar en el texto/etiquetas del artículo (Nivel 1)
                    contenedor = art.parent
                    tag_tiempo = contenedor.find(['time', 'span', 'div'], class_=re.compile(r'time|date|hora|fecha', re.I))
                    if tag_tiempo:
                        hora_encontrada = tag_tiempo.get_text().strip()
                    
                    # 2. Si no hay, buscar en la URL (Nivel 2)
                    if not hora_encontrada or len(hora_encontrada) < 3:
                        hora_encontrada = extraer_hora_url(full_link)
                    
                    # 3. Si sigue sin haber, usar metadatos (Nivel 3)
                    if not hora_encontrada:
                        hora_encontrada = meta_txt

                    data_raw += f"SITIO: {fuente['nombre']} | HORA_DATA: {hora_encontrada} | TEMA: {titulo} | LINK: {full_link}\n"
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
                    status_ia.text(f"⚖️ Verificando jerarquía de horas...")
                    model = genai.GenerativeModel(modelo_valido)
                    
                    prompt = f"""
                    FECHA ACTUAL: {fecha_ref}. HORA ACTUAL: {ahora.strftime('%H:%M')}.
                    
                    INSTRUCCIONES PARA LA HORA:
                    El campo 'HORA_DATA' contiene la información recolectada.
                    1. Si 'HORA_DATA' contiene una hora clara (HH:MM), ÚSALA.
                    2. Si 'HORA_DATA' es una fecha larga o metadato, extrae solo la hora.
                    3. Si no es clara, búscala en el texto del 'LINK'.
                    4. Si no hay rastro en ninguno, pon una hora estimada de hoy y añade "(aprox.)".

                    ORDEN DE SALIDA:
                    *TITULAR EN MAYÚSCULAS Y NEGRITA*
                    MEDIO EN MAYÚSCULAS Y NEGRITA
                    HH:MM (Solo los números, sin palabras adicionales)
                    Párrafo informativo (4 a 6 líneas).
                    URL

                    DATOS DE ENTRADA:
                    {noticias_raw}
                    """
                    
                    response = model.generate_content(prompt)
                    status_ia.empty()
                    
                    if response.text:
                        st.subheader("📋 Resultado Jerarquizado (Times New Roman 10):")
                        processed_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', response.text)
                        html_content = processed_text.replace("\n", "<br>")
                        
                        styled_html = f"""
                        <div style="font-family: 'Times New Roman', serif; font-size: 13.3px; color: black; background-color: white; padding: 25px; border: 1px solid #ccc; line-height: 1.3; text-align: justify;">
                            {html_content}
                        </div>
                        """
                        st.markdown(styled_html, unsafe_allow_html=True)
                        st.success("Copia el texto de arriba para tu informe.")
                except Exception as e:
                    st.error(f"Error: {e}")
