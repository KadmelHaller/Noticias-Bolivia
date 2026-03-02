import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import time

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")

# --- LÓGICA DE TIEMPO BOLIVIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
dia_semana = ahora.weekday() # 0 es Lunes
hora_actual = ahora.hour

# Determinar rango de búsqueda según tu nueva regla
if dia_semana == 0 and hora_actual < 12:
    # Lunes por la mañana: Incluye fin de semana
    rango_dias = "del sábado, domingo y lunes (Reporte Matutino)"
    fecha_ref = f"Noticias desde el {(ahora - timedelta(days=2)).strftime('%d/%m/%Y')} al {ahora.strftime('%d/%m/%Y')}"
    prompt_regla = "Como es LUNES POR LA MAÑANA, incluye noticias relevantes desde el sábado pasado hasta hoy."
else:
    # Lunes tarde o cualquier otro día: Solo hoy
    rango_dias = f"exclusivamente de hoy {ahora.strftime('%d/%m/%Y')} (Reporte Vespertino)"
    fecha_ref = f"Noticias de hoy {ahora.strftime('%d/%m/%Y')}"
    prompt_regla = "SOLO incluye noticias publicadas HOY. Ignora cualquier noticia de días anteriores."

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
    headers = {'User-Agent': 'Mozilla/5.0'}
    data_raw = ""
    pb = st.progress(0)
    for i, fuente in enumerate(fuentes):
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            # Si es tarde, bajamos el límite de escaneo para que sea más rápido
            limite = 10 if hora_actual >= 12 else 20
            for tag in soup.find_all(['h1', 'h2', 'h3'], limit=limite):
                titulo = tag.get_text().strip()
                a_tag = tag.find('a') or tag.find_parent('a')
                if a_tag and a_tag.get('href') and len(titulo) > 30:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'].rstrip('/') + link
                    data_raw += f"MEDIO: {fuente['nombre']} | TEMA: {titulo} | LINK: {full_link}\n"
        except: continue
    pb.empty()
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    
    if st.button('🚀 GENERAR MONITOREO'):
        # --- DETECCIÓN DE MODELO ---
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
                    status_ia.text(f"⚖️ IA analizando noticias ({rango_dias})...")
                    model = genai.GenerativeModel(modelo_valido)
                    
                    prompt = f"""
                    FECHA DEL REPORTE: {fecha_ref}.
                    {prompt_regla}
                    
                    TAREA: Resumen técnico para LibreOffice Writer. 
                    No uses asteriscos (*) ni negritas de Markdown. Solo texto plano.
                    
                    ENTRADA DE DATOS:
                    {noticias_raw}
                    
                    PRIORIDAD TEMÁTICA: Economía, Impuestos, Aduana, Gestión Pública.
                    PRIORIDAD REGIONAL: Cochabamba y Tarija.

                    FORMATO DE SALIDA (ESTRICTO):
                    TITULAR (MAYÚSCULAS Y NEGRITAS, TEXTO CON UN SÍMBOLO ASTERISCO AL PRINCIPIO DEL TITULAR Y UN SÍMBOLO ASTERISCO AL FINAL DEL TITULAR)
                    MEDIO (MAYÚSCULAS Y NEGRITAS)
                    Párrafo técnico informativo de 5 líneas sin opiniones.
                    URL
                    (IMPORTANTE: Deja 2 líneas vacías entre noticias).
                    """
                    
                    response = model.generate_content(prompt)
                    status_ia.empty()
                    
                    if response.text:
                        st.subheader("Copia para LibreOffice Writer:")
                        st.text_area(label="Texto Limpio", value=response.text, height=600)
                        
                        st.download_button(
                            label="📄 Descargar (.txt)",
                            data=response.text,
                            file_name=f"monitoreo_{ahora.strftime('%H%M')}_{ahora.strftime('%d_%m_%Y')}.txt",
                            mime="text/plain"
                        )
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("No se capturaron suficientes noticias.")
