import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import time

st.set_page_config(page_title="Monitoreo Bolivia", page_icon="🇧🇴")

# --- CONFIGURACIÓN DE TIEMPO ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO DE PRENSA: {fecha_hoy_bonita}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_cuerpo_nota(url, headers):
    """Extrae el texto de la noticia de forma simple y sin filtros de hora."""
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Limpieza básica
        for s in soup(["script", "style", "nav", "footer", "header"]):
            s.decompose()
            
        # Extraer párrafos
        parrafos = soup.find_all('p', limit=8)
        texto = " ".join([p.get_text().strip() for p in parrafos if len(p.get_text()) > 20])
        
        return texto
    except:
        return ""

def buscar_noticias():
    fuentes = [
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/"},
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/"},
        {"nombre": "UNITEL", "url": "https://unitel.bo/noticias/economia"},
        {"nombre": "RED UNO", "url": "https://www.reduno.com.bo/"},
        {"nombre": "ATB", "url": "https://www.atb.com.bo/"},
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/"},
        {"nombre": "BOLIVISION", "url": "https://www.redbolivision.tv.bo/"},
        {"nombre": "URGENTE BO", "url": "https://www.urgente.bo/"},
        {"nombre": "IN NOTICIAS", "url": "https://innoticiasbo.com/"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
    datos_acumulados = ""
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
        st.write(f"🔍 Buscando en {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Buscamos todos los enlaces que parezcan noticias
            enlaces = soup.find_all('a', href=True)
            vistos = set()
            procesados = 0
            
            for link in enlaces:
                url_n = link['href']
                texto_n = link.get_text().strip()
                
                # Normalizar URL
                if url_n.startswith('/'):
                    base = fuente['url'].split('.bo')[0] + '.bo'
                    url_n = base + url_n
                
                # Filtros de seguridad para evitar basura
                if len(texto_n) < 30 or url_n in vistos or any(x in url_n for x in ['/tag/', '/category/', 'facebook', 'twitter']):
                    continue
                
                # Extraer cuerpo
                cuerpo = extraer_cuerpo_nota(url_n, headers)
                
                if len(cuerpo) > 150:
                    datos_acumulados += f"MEDIO: {fuente['nombre']} | TITULAR: {texto_n} | LINK: {url_n} | TEXTO: {cuerpo[:800]}\n\n"
                    vistos.add(url_n)
                    procesados += 1
                
                if procesados >= 6: break # Límite por medio para no saturar
        except Exception as e:
            st.warning(f"No se pudo acceder a {fuente['nombre']}")
            continue
            
    return datos_acumulados

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE (MODO CONTENIDO)'):
        noticias_raw = buscar_noticias()
        
        if len(noticias_raw) > 500:
            modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model = genai.GenerativeModel(next((m for m in modelos if "1.5-flash" in m), modelos[0]))
            
            prompt = f"""
            HOY ES: {fecha_hoy_bonita}.
            
            TAREA DE FILTRADO:
            - Solo incluye noticias de Economía, Impuestos, Aduana, Gobierno, Gestión Municipal o Conflictos Sociales.
            - ELIMINA TODO sobre Deportes, Farándula, Horóscopos, Cine e Internacional (a menos que afecte directamente a Bolivia).
            - PRIORIZA noticias de Cochabamba y Tarija.

            FORMATO DE SALIDA:
            - Una lista continua (no agrupar por medio).
            - Si el texto no menciona explícitamente la hora, pon la hora actual {ahora.strftime('%H:%M')} seguida de "(aprox.)".
            
            ESTRUCTURA POR NOTICIA:
            *TITULAR EN MAYÚSCULAS Y NEGRITA*
            MEDIO EN MAYÚSCULAS Y NEGRITA
            HH:MM
            Resumen de 4 a 6 líneas (muy detallado).
            URL
            """
            
            with st.spinner("IA analizando contenido..."):
                res = model.generate_content([prompt, noticias_raw])
            
            if res.text:
                st.subheader("📋 Resultado del Monitoreo:")
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        else:
            st.error("No se recolectaron suficientes noticias. Revisa la conexión.")
