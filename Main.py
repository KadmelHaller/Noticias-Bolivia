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
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/section/pais", "base": "https://www.opinion.com.bo"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/actualidad/economia", "base": "https://www.lostiempos.com"},
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/category/bolivia/", "base": "https://lavozdetarija.com"},
        {"nombre": "UNITEL", "url": "https://unitel.bo/economia/", "base": "https://unitel.bo"},
        {"nombre": "RED UNO", "url": "https://www.reduno.com.bo/noticias", "base": "https://www.redbolivision.tv.bo"},
        {"nombre": "ATB", "url": "https://www.atb.com.bo/", "base": "https://www.atb.com.bo"},
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/principal/noticias", "base": "https://www.boliviatv.bo"},
        {"nombre": "URGENTE BO", "url": "https://www.urgente.bo/", "base": "https://www.urgente.bo"},
        {"nombre": "IN NOTICIAS", "url": "https://innoticiasbo.com/", "base": "https://innoticiasbo.com"},
        {"nombre": "ENFOQUE NEWS", "url": "https://enfoquenews.com.bo/", "base": "https://enfoquenews.com.bo"}
    ]
    
    # Headers más robustos para evitar bloqueos
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    }
    
    data_raw = ""
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
        pb.progress((i + 1) / len(fuentes))
        try:
            # Aumentamos el timeout y usamos una sesión para manejar cookies
            session = requests.Session()
            r = session.get(fuente['url'], headers=headers, timeout=15)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')

            # Buscamos noticias en diversas etiquetas comunes
            articulos = soup.find_all(['h1', 'h2', 'h3', 'article'], limit=25)
            
            for art in articulos:
                a_tag = art.find('a') if art.name != 'a' else art
                titulo = art.get_text().strip()
                
                if a_tag and a_tag.get('href') and len(titulo) > 25:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'].rstrip('/') + link
                    
                    # Intentar extraer fecha/hora del texto del contenedor o del propio link (algunos links llevan la fecha)
                    contexto_txt = art.parent.get_text()[:200] # Tomamos un poco de texto alrededor
                    
                    data_raw += f"MEDIO: {fuente['nombre']} | CONTEXTO: {contexto_txt} | TEMA: {titulo} | LINK: {full_link}\n"
        except Exception as e:
            continue
            
    pb.empty()
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    
    if st.button('🚀 GENERAR MONITOREO'):
        modelo_valido = None
        try:
            # Lista de modelos para asegurar compatibilidad
            modelos_compatibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            modelo_valido = next((m for m in modelos_compatibles if "1.5-flash" in m), modelos_compatibles[0])
        except: pass

        if modelo_valido:
            noticias_raw = extraer_noticias()
            if len(noticias_raw) > 300:
                status_ia = st.empty()
                try:
                    status_ia.text(f"⚖️ IA analizando noticias de múltiples medios...")
                    model = genai.GenerativeModel(modelo_valido)
                    
                    prompt = f"""
                    FECHA DEL REPORTE: {fecha_ref}.
                    {prompt_regla}
                    
                    TAREA: Resumen técnico para monitoreo de prensa.
                    
                    PRIORIDAD: 1. Economía e Impuestos, 2. Govierno, 3. Cochabamba y Tarija. 4. Orden de medios: Opinión, Los Tiempos, La Voz de Tarija, TV, medios digitales.
                    REGLA CRÍTICA DE HORA: Revisa el campo 'CONTEXTO' y el 'LINK' para encontrar la hora. Si el link dice algo como '/2024/03/02/14-30/', la hora es 14:30. Si no hay nada, estima una hora lógica de hoy lunes entre las 07:00 y las {ahora.strftime('%H:%M')}. No pongas "Hora no disponible", asume una hora basada en la frescura.

                    ENTRADA: {noticias_raw}

                    ORDEN DE SALIDA (ESTRICTO):
                    *TITULAR EN MAYÚSCULAS Y NEGRITA* (con un asterisco al principio y otro al final)
                    MEDIO EN MAYÚSCULAS Y NEGRITA
                    HH:MM (Solo la hora, sin etiquetas)
                    Párrafo informativo (4 a 6 líneas).
                    URL (en minúsculas).

                    (Exactamente un salto de línea entre noticias. Sin asteriscos de markdown excepto en el titular).
                    """
                    
                    response = model.generate_content(prompt)
                    status_ia.empty()
                    
                    if response.text:
                        st.subheader("📋 Formato Times New Roman 10 (Listo para copiar):")
                        
                        # Limpieza de negritas Markdown a HTML
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
                        st.success("Monitoreo generado con éxito.")
                except Exception as e:
                    st.error(f"Error en la IA: {e}")
            else:
                st.error("Los medios bloquearon la conexión o no hay noticias nuevas. Intenta de nuevo.")
