import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import os

st.set_page_config(page_title="Monitoreo Bolivia Pro", page_icon="🇧🇴", layout="wide")

# --- LÓGICA DE TIEMPO Y PERSISTENCIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')
HISTORIAL_FILE = "noticias_vistas.txt"

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def guardar_en_historial(url):
    with open(HISTORIAL_FILE, "a") as f:
        f.write(url + "\n")

st.title(f"📰 MONITOREO TÉCNICO: {fecha_hoy_bonita}")
st.sidebar.info(f"Última actualización: {ahora.strftime('%H:%M:%S')}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_monitoreo():
    # FUENTES AMPLIADAS: COCHABAMBA (Prioridad) + SANTA CRUZ + INFLUENCERS (Vía News)
    fuentes = [
        # COCHABAMBA (Primera Instancia)
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/"},
        # SANTA CRUZ (Segunda Instancia)
        {"nombre": "EL DEBER", "url": "https://eldeber.com.bo/"},
        {"nombre": "EL DÍA", "url": "https://www.eldia.com.bo/"},
        {"nombre": "EL MUNDO", "url": "https://elmundo.com.bo/"},
        {"nombre": "LA ESTRELLA DEL ORIENTE", "url": "https://www.laestrelladeloriente.com/"},
        # NACIONALES Y OTROS
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/"},
        {"nombre": "LA RAZÓN", "url": "https://larazon.bo/"},
        {"nombre": "UNITEL", "url": "https://unitel.bo/noticias/economia"},
        # INFLUENCERS / OPINIÓN (Simulación mediante búsqueda de keywords en medios de opinión)
        {"nombre": "INFLUENCERS/OPINIÓN", "url": "https://www.google.com/search?q=impuestos+bolivia+influencers+opinión&tbm=nws"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}
    data_final = ""
    historial = cargar_historial()
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
        st.write(f"📡 Revisando {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=15)
            if r.status_code != 200: continue
            
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            procesados = 0
            
            for l in links:
                url_n = l['href']
                if not url_n.startswith('http'):
                    url_n = fuente['url'].rstrip('/') + "/" + url_n.lstrip('/')
                
                # FILTRO DE DUPLICADOS: Si ya se extrajo en el turno de las 08:30, se salta en el de las 13:30
                if url_n in historial:
                    continue
                
                texto_enlace = l.get_text().strip()
                if len(texto_enlace) < 25 or any(x in url_n for x in ['/tag/', '/autor/', '/category/']): 
                    continue
                
                try:
                    rn = requests.get(url_n, headers=headers, timeout=10)
                    if rn.status_code != 200: continue
                    soup_n = BeautifulSoup(rn.text, 'html.parser')
                    cuerpo = " ".join([p.get_text().strip() for p in soup_n.find_all('p', limit=6) if len(p.get_text()) > 25])
                    
                    if len(cuerpo) > 150:
                        # Priorizamos contenido de IMPUESTOS mediante un filtro de texto simple antes de enviar a IA
                        if "impuesto" in cuerpo.lower() or "impuesto" in texto_enlace.lower() or "sin" in cuerpo.lower():
                            data_final += f"MEDIO: {fuente['nombre']} | TITULAR: {texto_enlace} | TXT: {cuerpo[:900]} | LINK: {url_n}\n\n"
                            guardar_en_historial(url_n)
                            procesados += 1
                except: continue
                if procesados >= 5: break
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 EJECUTAR MONITOREO PROGRAMADO'):
        raw_data = procesar_monitoreo()
        if len(raw_data) > 300:
            try:
                model = genai.GenerativeModel('models/gemini-flash-latest')
                prompt = f"""
                HOY ES: {fecha_hoy_bonita}.
                OBJETIVO: Monitoreo especializado en IMPUESTOS.
                
                JERARQUÍA DE IMPORTANCIA:
                1. IMPUESTOS EN COCHABAMBA (Prioridad absoluta).
                2. IMPUESTOS EN SANTA CRUZ (El Deber, El Día, El Mundo, Estrella del Oriente).
                3. OPINIÓN DE INFLUENCERS/REDES sobre impuestos.
                
                ORDEN DE PRESENTACIÓN:
                - Primero noticias de Cochabamba.
                - Segundo noticias de Santa Cruz.
                - Tercero Influencers y resto de medios.
                
                ESTRUCTURA (MANTENER FORMATO):
                **TITULAR EN MAYÚSCULAS**
                **NOMBRE DEL MEDIO EN MAYÚSCULAS**
                Resumen detallado enfocado en el impacto tributario (4-6 líneas).
                URL directo, sin etiqueta.
                """
                res = model.generate_content([prompt, raw_data])
                st.subheader("📋 Resumen Informativo Actualizado:")
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error con el modelo Gemini: {str(e)}")
        else:
            st.warning("No se encontraron noticias nuevas sobre IMPUESTOS en este turno.")
