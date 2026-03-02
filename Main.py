import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import time

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
dia_semana = ahora.weekday() # 0 es Lunes

if dia_semana == 0:
    rango_dias = "del sábado, domingo y hoy lunes"
    fecha_referencia = f"HOY es {ahora.strftime('%d/%m/%Y')}, pero incluye noticias relevantes desde el sábado {(ahora - timedelta(days=2)).strftime('%d/%m/%Y')}"
else:
    rango_dias = "de hoy"
    fecha_referencia = f"HOY {ahora.strftime('%d/%m/%Y')}"

st.title(f"📰 MONITOREO DE NOTICIAS: {ahora.strftime('%d/%m/%Y')}")
st.info(f"Criterio de búsqueda: Noticias {rango_dias}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

# --- FUNCIÓN DE AUTODETECCIÓN (LA QUE EVITA EL 404) ---
def obtener_ruta_modelo(key):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(url)
        if res.status_code == 200:
            modelos = res.json().get('models', [])
            for m in modelos:
                if "gemini-1.5-flash" in m['name']:
                    return m['name']
        return "models/gemini-1.5-flash"
    except: return "models/gemini-1.5-flash"

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
    st_text = st.empty()
    
    for i, fuente in enumerate(fuentes):
        st_text.text(f"🔍 [{int(((i+1)/len(fuentes))*100)}%] Escaneando: {fuente['nombre']}...")
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
    st_text.empty()
    pb.empty()
    return data_raw

if api_key:
    if st.button('🚀 GENERAR MONITOREO'):
        noticias_raw = extraer_noticias()
        if len(noticias_raw) > 300:
            status_ia = st.empty()
            pb_ia = st.progress(0)
            for p in range(0, 96, 4):
                status_ia.text(f"⚖️ Procesando información con IA... {p}%")
                pb_ia.progress(p / 100)
                time.sleep(0.05)
            
            # --- CONSTRUCCIÓN SEGURA DE URL ---
            ruta = obtener_ruta_modelo(api_key)
            url_api = f"https://generativelanguage.googleapis.com/v1beta/{ruta}:generateContent?key={api_key}"
            
            prompt = f"""
            FECHA: {fecha_referencia}.
            TAREA: Resumen informativo técnico.
            REGLA DE FORMATO: No uses asteriscos (*) ni símbolos de Markdown. Solo texto plano.
            
            ENTRADA:
            {noticias_raw}
            
            REGLAS DE FILTRADO:
            - Prioridad: Economía, Impuestos, Cochabamba, Tarija.
            
            FORMATO DE SALIDA PARA LIBREOFFICE:
            TITULAR (EN MAYÚSCULAS)
            MEDIO (EN MAYÚSCULAS)
            Párrafo descriptivo de 4 a 6 líneas.
            URL (en minúsculas)
            
            (IMPORTANTE: Deja dos saltos de línea vacíos entre noticias).
            """
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]],
                "generationConfig": {"temperature": 0.0}
            }
            
            res = requests.post(url_api, json=payload)
            status_ia.empty()
            pb_ia.empty()
            
            if res.status_code == 200:
                texto_final = res.json()['candidates'][0]['content']['parts'][0]['text']
                
                # Cuadro de texto para copiar fácilmente
                st.subheader("Copia el texto de aquí abajo:")
                st.text_area(label="Resultado limpio para LibreOffice", value=texto_final, height=600)
                
                st.download_button(
                    label="📄 Descargar Monitoreo (.txt)",
                    data=texto_final,
                    file_name=f"monitoreo_{ahora.strftime('%d_%m_%Y')}.txt",
                    mime="text/plain"
                )
            else:
                st.error(f"Error {res.status_code}: Asegúrate de que la API Key sea correcta.")
        else:
            st.error("No se capturaron suficientes noticias de los portales.")
