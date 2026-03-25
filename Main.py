import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import os

st.set_page_config(page_title="Monitoreo Bolivia Pro", page_icon="🇧🇴", layout="wide")

# --- PERSISTENCIA INTELIGENTE (FILTRO > 1 HORA) ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')
HISTORIAL_FILE = "vistos_monitoreo.txt"

def gestionar_historial():
    if os.path.exists(HISTORIAL_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(HISTORIAL_FILE), zona_horaria)
        # Si pasó menos de una hora, devolvemos conjunto vacío para que NO restrinja nada
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
    # FUENTES ORGANIZADAS POR REGIÓN Y CATEGORÍA
    fuentes = [
        # --- COCHABAMBA ---
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "ATB COCHABAMBA", "u": "https://www.atb.com.bo/seccion/cochabamba", "t": "TV", "r": "Cochabamba"},
        {"n": "INFLUENCERS CBBA", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:tiktok.com+OR+site:instagram.com+impuestos+cochabamba+bolivia", "t": "Influencer", "r": "Cochabamba"},
        
        # --- SANTA CRUZ ---
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL DÍA", "u": "https://www.eldia.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "ESTRELLA DEL ORIENTE", "u": "https://www.laestrelladeloriente.com/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "UNITEL SANTA CRUZ", "u": "https://unitel.bo/santa-cruz", "t": "TV", "r": "Santa Cruz"},
        {"n": "INFLUENCERS SCZ", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:tiktok.com+OR+site:instagram.com+impuestos+santa+cruz+bolivia", "t": "Influencer", "r": "Santa Cruz"},

        # --- DIGITALES Y NACIONALES (Para complementar secciones) ---
        {"n": "URGENTE BO", "u": "https://www.urgente.bo/", "t": "Digital", "r": "Nacional"},
        {"n": "RED UNO", "u": "https://www.reduno.com.bo/", "t": "TV", "r": "Nacional"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}
    data_final = ""
    historial = gestionar_historial()
    pb = st.progress(0)
    
    for i, f in enumerate(fuentes):
        st.write(f"🔍 Escaneando {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            vistos = 0
            
            for l in links:
                url = l['href']
                if not url.startswith('http'): url = f['u'].rstrip('/') + "/" + url.lstrip('/')
                if url in historial: continue
                
                texto = l.get_text().strip()
                if len(texto) < 25: continue
                
                try:
                    rn = requests.get(url, headers=headers, timeout=8)
                    s_n = BeautifulSoup(rn.text, 'html.parser')
                    txt = " ".join([p.get_text().strip() for p in s_n.find_all('p', limit=4)])
                    
                    if len(txt) > 100:
                        data_final += f"REGION: {f['r']} | TIPO: {f['t']} | MEDIO: {f['n']} | TITULAR: {texto} | TXT: {txt[:850]} | LINK: {url}\n\n"
                        guardar_historial(url)
                        vistos += 1
                except: continue
                if vistos >= 6: break
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE COMPLETO (SISTEMA TRIPARTITO)'):
        raw_data = procesar_fuentes()
        if len(raw_data) > 300:
            try:
                model = genai.GenerativeModel('models/gemini-flash-latest')
                prompt = f"""
                FECHA: {fecha_hoy_bonita}.
                Actúa como un monitor de medios de alto nivel. Organiza el reporte siguiendo esta jerarquía numérica:

                1. COCHABAMBA:
                   1.1 MEDIOS ESCRITOS: Prioridad IMPUESTOS, luego resto de noticias.
                   1.2 CANALES DE TELEVISIÓN: Prioridad IMPUESTOS, luego resto.
                   1.3 MEDIOS DIGITALES: Prioridad IMPUESTOS, luego resto.
                   1.4 INFLUENCERS LOCALES (CBBA): Solo contenido relevante a impuestos.

                2. SANTA CRUZ:
                   1.1 MEDIOS ESCRITOS: Prioridad IMPUESTOS, luego resto.
                   1.2 CANALES DE TELEVISIÓN: Prioridad IMPUESTOS, luego resto.
                   1.3 MEDIOS DIGITALES: Prioridad IMPUESTOS, luego resto.
                   1.4 INFLUENCERS LOCALES (SCZ): Solo contenido relevante a impuestos.

                ESTRUCTURA DE CADA NOTICIA (SIN EXCEPCIÓN):
                **TITULAR EN MAYÚSCULAS**
                **NOMBRE DEL MEDIO EN MAYÚSCULAS**
                Resumen de 4 a 6 líneas. Si es de impuestos, detalla el impacto para el contribuyente.
                URL directo (sin etiquetas adicionales).

                Si no hay noticias de impuestos en una subcategoría, coloca las noticias más importantes de esa región/medio respetando el orden 1.1 al 1.4.
                """
                res = model.generate_content([prompt, raw_data])
                st.subheader("📋 Reporte Final de Monitoreo:")
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error con Gemini: {str(e)}")
        else:
            st.warning("No se encontraron noticias nuevas en este turno.")
