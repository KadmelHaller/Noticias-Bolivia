import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import time
import re

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")

# --- LÓGICA DE TIEMPO BOLIVIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
dia_semana = ahora.weekday() 
hora_actual = ahora.hour

if dia_semana == 0 and hora_actual < 12:
    rango_dias = "del sábado, domingo y lunes (Matutino)"
    fecha_ref = f"Noticias desde el {(ahora - timedelta(days=2)).strftime('%d/%m/%Y')} al {ahora.strftime('%d/%m/%Y')}"
    prompt_regla = "Incluye noticias relevantes desde el sábado pasado hasta hoy."
else:
    rango_dias = f"exclusivamente de hoy {ahora.strftime('%d/%m/%Y')} (Vespertino)"
    fecha_ref = f"Noticias de hoy {ahora.strftime('%d/%m/%Y')}"
    prompt_regla = "SOLO incluye noticias publicadas HOY lunes. Ignora días anteriores."

st.title(f"📰 MONITOREO DE NOTICIAS: {ahora.strftime('%d/%m/%Y')}")
st.info(f"Filtro activo: {rango_dias}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_noticias():
    fuentes = [
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/", "base": "https://www.opinion.com.bo"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/", "base": "https://www.lostiempos.com"},
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/", "base": "https://lavozdetarija.com"},
        {"nombre": "UNITEL", "url": "https://unitel.bo/economia/", "base": "https://unitel.bo"},
        {"nombre": "RED UNO", "url": "https://www.reduno.com.bo/", "base": "https://www.reduno.com.bo"},
        {"nombre": "ATB", "url": "https://www.atb.com.bo/", "base": "https://www.atb.com.bo"},
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/principal/", "base": "https://www.boliviatv.bo"},
        {"nombre": "URGENTE BO", "url": "https://www.urgente.bo/", "base": "https://www.urgente.bo"},
        {"nombre": "BOLIVISION", "url": "https://www.redbolivision.tv.bo/", "base": "https://www.redbolivision.tv.bo"},
        {"nombre": "CADENA A", "url": "https://www.cadenaa.tv/", "base": "https://www.cadenaa.tv"},
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
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # --- BÚSQUEDA DE HORA EN METADATOS DE LA PÁGINA PRINCIPAL ---
            # Muchos sitios ponen la hora en etiquetas ocultas tipo 'article:published_time'
            meta_date = ""
            meta_tag = soup.find("meta", property="article:published_time") or \
                       soup.find("meta", itemprop="datePublished") or \
                       soup.find("meta", name="publish-date")
            if meta_tag:
                meta_date = meta_tag.get("content", "")

            limite = 10 if hora_actual >= 12 else 20
            for tag in soup.find_all(['h1', 'h2', 'h3'], limit=limite):
                titulo = tag.get_text().strip()
                a_tag = tag.find('a') or tag.find_parent('a')
                
                if a_tag and a_tag.get('href') and len(titulo) > 30:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'].rstrip('/') + link
                    
                    # Intentar capturar hora visual cerca del titular
                    time_info = ""
                    parent = tag.parent
                    time_tag = parent.find('time') or parent.find(class_=re.compile('date|time|fecha', re.I))
                    if time_tag:
                        time_info = time_tag.get_text().strip()
                    else:
                        time_info = meta_date # Usar la de los metadatos si no hay visual
                    
                    data_raw += f"MEDIO: {fuente['nombre']} | HORA_METADATO: {time_info} | TEMA: {titulo} | LINK: {full_link}\n"
        except: continue
    pb.empty()
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    
    if st.button('🚀 GENERAR MONITOREO'):
        modelo_valido = None
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'gemini-1.5-flash' in m.name:
                        modelo_valido = m.name
                        break
            if not modelo_valido:
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        modelo_valido = m.name
                        break
        except: pass

        if modelo_valido:
            noticias_raw = extraer_noticias()
            if len(noticias_raw) > 300:
                status_ia = st.empty()
                try:
                    status_ia.text(f"⚖️ IA analizando noticias y metadatos...")
                    model = genai.GenerativeModel(modelo_valido)
                    
                    prompt = f"""
                    FECHA DEL REPORTE: {fecha_ref}.
                    {prompt_regla}
                    TAREA: Resumen técnico informativo. 
                    FORMATO: Solo texto plano, sin asteriscos ni negritas de Markdown.
                    PRIORIDAD TEMÁTICA: ECONOMÍA, IMPUESTOS, GOBIERNO, LUEGO POLÍTICA, NO TOMAR EN CUENTA DEPORTES, INTERNACIONAL NI FARÁNDULA
                    PRIORIDAD GEOGRÁFICA: COCHABAMBA, TARIJA
                    ENTRADA: {noticias_raw}

                    ORDEN DE SALIDA PARA CADA NOTICIA (ESTRICTO):
                    *TITULAR EN MAYÚSCULAS Y NEGRITA* (con un asterisco al inicio y otro al final)
                    MEDIO EN MAYÚSCULAS Y NEGRITA
                    Hora de publicación (Solo la hora, sin etiquetas como 'Hora:' ni nada parecido. Si es un formato largo de metadato, límpialo para que solo quede HH:MM).
                    Párrafo informativo (4 a 6 líneas).
                    URL (en minúsculas).
                    
                    (Deja exactamente un salto de línea entre noticias. Confirma nombres y cargos).
                    """
                    
                    response = model.generate_content(prompt)
                    status_ia.empty()
                    
                    if response.text:
                        st.subheader("📋 Formato Times New Roman 10 (Listo para copiar):")
                        
                        # Convertir negritas de Markdown a HTML
                        processed_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', response.text)
                        # Convertir saltos de línea a HTML
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
                        st.success("Copia el texto del recuadro superior.")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("No se capturaron noticias suficientes.")
