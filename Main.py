import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import os
from urllib.parse import urlparse, parse_qs

st.set_page_config(page_title="Monitoreo Bolivia Pro", page_icon="🇧🇴", layout="wide")

# --- CONFIGURACIÓN DE TIEMPO Y FILTROS ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')
HISTORIAL_FILE = "vistos_monitoreo.txt"

# Temas permitidos para el filtro de relevancia
TEMAS_OK = ["impuesto", "sin", "tribut", "factur", "fiscal", "econom", "gobiern", "arce", "dolar", "clausur", "aduana", "subsidio", "gasolina", "diesel", "presupuest"]

def gestionar_historial():
    if os.path.exists(HISTORIAL_FILE):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(HISTORIAL_FILE), zona_horaria)
            # Regla: Si la diferencia es < 1 hora, NO restringir (mostrar todo)
            if (ahora - mtime).total_seconds() < 3600:
                return set()
            with open(HISTORIAL_FILE, "r") as f:
                return set(f.read().splitlines())
        except:
            return set()
    return set()

def guardar_historial(url):
    with open(HISTORIAL_FILE, "a") as f:
        f.write(url + "\n")

def limpiar_url_google(url_google):
    """Extrae link directo de resultados de Google (RRSS)"""
    if "google.com/url" in url_google:
        parsed = urlparse(url_google)
        res = parse_qs(parsed.query).get('q')
        return res[0] if res else url_google
    return url_google

def es_relevante_y_actual(texto, url):
    txt = texto.lower()
    if any(old in txt for old in ["2021", "2022", "2023"]): return False
    return any(t in txt for t in TEMAS_OK) or any(t in url.lower() for t in TEMAS_OK)

st.title(f"📰 MONITOREO ESTRATÉGICO: {fecha_hoy_bonita}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_fuentes():
    fuentes = [
        # --- COCHABAMBA ---
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "t": "Escrito", "r": "Cochabamba"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/seccion/cochabamba/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "ATB CBBA", "u": "https://www.atb.com.bo/seccion/cochabamba", "t": "TV", "r": "Cochabamba"},
        {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:tiktok.com+OR+site:instagram.com+OR+site:x.com+impuestos+cochabamba+2026", "t": "Influencer", "r": "Cochabamba"},
        
        # --- SANTA CRUZ ---
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/economia", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL MUNDO", "u": "https://elmundo.com.bo/category/economia/", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "EL DÍA", "u": "https://www.eldia.com.bo/index.php?cat=357", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "UNITEL SCZ", "u": "https://unitel.bo/santa-cruz", "t": "TV", "r": "Santa Cruz"},
        {"n": "RRSS SCZ", "u": "
