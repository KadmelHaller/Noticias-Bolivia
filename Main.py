import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import time

# Configuración de página
st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
dia_semana = ahora.weekday() # 0 es Lunes

# Lógica de fechas para el reporte
if dia_semana == 0:
    rango_dias = "del sábado, domingo y lunes"
    fecha_ref = f"Noticias desde el {(ahora - timedelta(days=2)).strftime('%d/%m/%Y')} al {ahora.strftime('%d/%m/%Y')}"
else:
    rango_dias = "de hoy"
    fecha_ref = f"Noticias de hoy {ahora.strftime('%d/%m/%Y')}"

st.title(f"📰 MONITOREO DE NOTICIAS: {ahora.strftime('%d/%m/%Y')}")
st.info(f"Criterio de búsqueda: {rango_dias}")

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
    st_status = st.empty()
    
    for i, fuente in enumerate(fuentes):
        porcentaje = int(((i + 1) / len(fuentes)) * 100)
        st_status.text(f"🔍 [{porcentaje}%] Escaneando: {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            limite = 20 if dia_semana == 0 else 12
            for tag in soup.find_all(['h1', 'h2', 'h3'], limit=limite):
                titulo = tag.get_text().strip()
                a_tag = tag.find('a') or tag.find_parent('a')
                if a_tag and a_tag.get('href') and len(titulo) > 30:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'].rstrip('/') + link
                    data_raw += f"MEDIO: {fuente['nombre']} | TEMA: {titulo} | LINK: {full_link}\n"
        except: continue
    
    st_status.empty()
    pb.empty()
    return data_raw

if api_key:
    # CONFIGURACIÓN DE LA LIBRERÍA OFICIAL
    genai.configure(api_key=api_key)
    
    if st.button('🚀 GENERAR MONITOREO'):
        noticias_raw = extraer_noticias()
        
        if len(noticias_raw) > 300:
            status_ia = st.empty()
            pb_ia = st.progress(0)
            
            # Simulamos progreso visual para la IA
            for p in range(0, 101, 5):
                status_ia.text(f"⚖️ Procesando información con IA... {p}%")
                pb_ia.progress(p / 100)
                time.sleep(0.1)

            try:
                # LLAMADA A TRAVÉS DE LA LIBRERÍA (Evita el 404)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""
                FECHA: {fecha_ref}.
                TAREA: Resumen técnico para LibreOffice Writer.
                IMPORTANTE: No uses asteriscos (*) ni negritas de Markdown. Solo texto plano.
                
                ENTRADA:
                {noticias_raw}
                
                REGLAS:
                - Prioridad temas de Economía e Impuestos.
                - Prioridad regional: Cochabamba y Tarija.
                
                FORMATO:
                TITULAR (MAYÚSCULAS)
                MEDIO (MAYÚSCULAS)
                Resumen descriptivo de 5 líneas.
                URL (minúsculas)
                (Deja 2 líneas vacías entre cada noticia).
                """
                
                response = model.generate_content(prompt)
                
                status_ia.empty()
                pb_ia.empty()
                
                if response.text:
                    st.subheader("Resultado para copiar y pegar:")
                    # Usamos text_area para facilitar el copiado limpio
                    st.text_area(label="Contenido para LibreOffice", value=response.text, height=600)
                    
                    st.download_button(
                        label="📄 Descargar en formato .txt",
                        data=response.text,
                        file_name=f"monitoreo_{ahora.strftime('%d_%m_%Y')}.txt",
                        mime="text/plain"
                    )
            except Exception as e:
                status_ia.empty()
                pb_ia.empty()
                st.error(f"Error al conectar con Gemini: {str(e)}")
        else:
            st.error("No se capturaron suficientes titulares de los medios.")
