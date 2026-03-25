import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import os

st.set_page_config(page_title="Monitoreo Bolivia Pro", page_icon="🇧🇴", layout="wide")

# --- LÓGICA DE TIEMPO Y PERSISTENCIA INTELIGENTE ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')
HISTORIAL_FILE = "vistos_monitoreo.txt"

def gestionar_historial():
    """Retorna el historial de URLs solo si la última actualización fue hace más de 1 hora"""
    if os.path.exists(HISTORIAL_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(HISTORIAL_FILE), zona_horaria)
        # Si la diferencia es menor a 1 hora (3600 seg), ignoramos el filtro para mostrar todo
        if (ahora - mtime).total_seconds() < 3600:
            return set()
        with open(HISTORIAL_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def guardar_historial(url):
    with open(HISTORIAL_FILE, "a") as f:
        f.write(url + "\n")

st.title(f"📰 MONITOREO ESTRATÉGICO: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_fuentes():
    # FUENTES ORGANIZADAS POR REGIÓN Y TIPO
    fuentes = [
        # COCHABAMBA
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/", "tipo": "Escrito", "region": "Cochabamba"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/", "tipo": "Escrito", "region": "Cochabamba"},
        
        # SANTA CRUZ
        {"nombre": "EL DEBER", "url": "https://eldeber.com.bo/", "tipo": "Escrito", "region": "Santa Cruz"},
        {"nombre": "EL DÍA", "url": "https://www.eldia.com.bo/", "tipo": "Escrito", "region": "Santa Cruz"},
        {"nombre": "EL MUNDO", "url": "https://elmundo.com.bo/", "tipo": "Escrito", "region": "Santa Cruz"},
        {"nombre": "LA ESTRELLA DEL ORIENTE", "url": "https://www.laestrelladeloriente.com/", "tipo": "Escrito", "region": "Santa Cruz"},
        
        # CANALES TV (NACIONAL CON FILTRO REGIONAL EN PROMPT)
        {"nombre": "UNITEL", "url": "https://unitel.bo/noticias/economia", "tipo": "TV", "region": "Nacional"},
        {"nombre": "RED UNO", "url": "https://www.reduno.com.bo/", "tipo": "TV", "region": "Nacional"},
        {"nombre": "ATB", "url": "https://www.atb.com.bo/", "tipo": "TV", "region": "Nacional"},
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/", "tipo": "TV", "region": "Nacional"},
        
        # DIGITALES E INFLUENCERS (RRSS)
        {"nombre": "URGENTE BO", "url": "https://www.urgente.bo/", "tipo": "Digital", "region": "Nacional"},
        {"nombre": "FACEBOOK/TIKTOK/X/IG", "url": "https://www.google.com/search?q=site:facebook.com+OR+site:tiktok.com+OR+site:x.com+OR+site:threads.net+impuestos+bolivia", "tipo": "Influencer", "region": "RRSS"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}
    data_final = ""
    historial = gestionar_historial()
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
        st.write(f"📡 {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            procesados = 0
            
            for l in links:
                url_n = l['href']
                if not url_n.startswith('http'):
                    url_n = fuente['url'].rstrip('/') + "/" + url_n.lstrip('/')
                
                if url_n in historial: continue
                
                texto_enlace = l.get_text().strip()
                if len(texto_enlace) < 25: continue
                
                try:
                    rn = requests.get(url_n, headers=headers, timeout=8)
                    soup_n = BeautifulSoup(rn.text, 'html.parser')
                    cuerpo = " ".join([p.get_text().strip() for p in soup_n.find_all('p', limit=5)])
                    
                    if len(cuerpo) > 120:
                        data_final += f"REGION: {fuente['region']} | TIPO: {fuente['tipo']} | MEDIO: {fuente['nombre']} | TITULAR: {texto_enlace} | TXT: {cuerpo[:800]} | LINK: {url_n}\n\n"
                        guardar_historial(url_n)
                        procesados += 1
                except: continue
                if procesados >= 6: break
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE JERÁRQUICO'):
        raw_data = procesar_fuentes()
        if len(raw_data) > 300:
            try:
                model = genai.GenerativeModel('models/gemini-flash-latest')
                prompt = f"""
                HOY ES: {fecha_hoy_bonita}.
                Genera un informe con este ORDEN ESTRICTO:

                1. COCHABAMBA:
                   1.1 MEDIOS ESCRITOS: (Prioridad IMPUESTOS, luego resto).
                   1.2 CANALES DE TELEVISIÓN: (Prioridad IMPUESTOS, luego resto).
                   1.3 MEDIOS DIGITALES: (Prioridad IMPUESTOS, luego resto).
                   1.4 INFLUENCERS/RRSS: (Solo sobre IMPUESTOS).

                2. SANTA CRUZ:
                   1.1 MEDIOS ESCRITOS (El Deber, El Día, El Mundo, Estrella): (Prioridad IMPUESTOS, luego resto).
                   1.2 CANALES DE TELEVISIÓN: (Prioridad IMPUESTOS, luego resto).
                   1.3 MEDIOS DIGITALES: (Prioridad IMPUESTOS, luego resto).
                   1.4 INFLUENCERS/RRSS: (Solo sobre IMPUESTOS).

                ESTRUCTURA DE CADA NOTICIA:
                **TITULAR EN MAYÚSCULAS**
                **NOMBRE DEL MEDIO EN MAYÚSCULAS**
                Resumen de 4-6 líneas enfocado en la relevancia técnica o tributaria.
                URL directo (sin etiquetas).

                Regla de Oro: Si la noticia es de IMPUESTOS, debe aparecer al principio de su respectiva subcategoría.
                """
                res = model.generate_content([prompt, raw_data])
                st.subheader("📋 Resumen Informativo:")
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error con Gemini: {str(e)}")
