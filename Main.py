import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import json

st.set_page_config(page_title="Monitoreo Bolivia Pro", page_icon="🇧🇴", layout="wide")

# --- LÓGICA DE TIEMPO BOLIVIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO TÉCNICO: {fecha_hoy_bonita}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_hora_especifica(soup, medio):
    """Mejora en la captura de horas para evitar campos vacíos"""
    texto = soup.get_text(" ", strip=True)
    
    # 1. Metadatos (Efectivo en La Razón, Unitel y El Deber)
    meta_time = soup.find("meta", property="article:published_time") or soup.find("meta", itemprop="datePublished")
    if meta_time:
        m = re.search(r'(\d{2}):(\d{2})', meta_time.get("content", ""))
        if m: return f"{m.group(1)}:{m.group(2)}"

    # 2. JSON-LD
    for s in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(s.string)
            nodes = data.get('@graph', [data]) if isinstance(data, dict) else data
            for node in (nodes if isinstance(nodes, list) else [nodes]):
                ds = node.get('datePublished', '')
                m = re.search(r'T(\d{2}):(\d{2})', ds)
                if m:
                    hh, mm = int(m.group(1)), m.group(2)
                    if medio == "ATB": hh = (hh - 4) % 24
                    return f"{hh:02d}:{mm}"
        except: continue

    # 3. Reglas específicas por medio
    if medio == "OPINIÓN":
        cuerpo = soup.find('article') or soup.find('div', class_='cuerpo')
        if cuerpo:
            m = re.search(r'(\d{1,2}:\d{2})', cuerpo.get_text())
            if m: return m.group(1)
    if medio == "LOS TIEMPOS":
        m = re.search(r'(\d{1,2})h(\d{2})', texto)
        if m: return f"{m.group(1)}:{m.group(2)}"
    
    # 4. Búsqueda de patrón general
    matches = re.findall(r'(\d{1,2}:\d{2})', texto)
    for m in matches:
        if m != ahora.strftime('%H:%M') and m != "04:00": return m
    return "Sin hora"

def procesar_monitoreo():
    fuentes = [
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/"},
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/"},
        {"nombre": "LA RAZÓN", "url": "https://larazon.bo/"},
        {"nombre": "UNITEL", "url": "https://unitel.bo/noticias/economia"},
        {"nombre": "RED UNO", "url": "https://www.reduno.com.bo/"},
        {"nombre": "ATB", "url": "https://www.atb.com.bo/"},
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/"},
        {"nombre": "BOLIVISION", "url": "https://www.redbolivision.tv.bo/"},
        {"nombre": "URGENTE BO", "url": "https://www.urgente
