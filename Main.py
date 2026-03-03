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
    texto = soup.get_text(" ", strip=True)
    # 1. OPINIÓN: Ignorar cabecera
    if medio == "OPINIÓN":
        cuerpo = soup.find('article') or soup.find('div', class_='cuerpo')
        if cuerpo:
            m = re.search(r'(\d{1,2}:\d{2})', cuerpo.get_text())
            if m: return m.group(1)
    # 2. LOS TIEMPOS: 13h55 -> 13:55
    if medio == "LOS TIEMPOS":
        m = re.search(r'(\d{1,2})h(\d{2})', texto)
        if m: return f"{m.group(1)}:{m.group(2)}"
    # 5. UNITEL: Relativo
    if medio == "UNITEL":
        m_rel = re.search(r'hace\s+(\d+)\s+(minuto|hora)', texto.lower())
        if m_rel:
            cant = int(m_rel.group(1))
            delta = timedelta(minutes=cant) if 'min' in m_rel.group(2) else timedelta(hours=cant)
            return (ahora - delta).strftime('%H:%M')
    # Metadatos
    if medio in ["ATB", "IN NOTICIAS", "ENFOQUE NEWS"]:
        for s in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(s.string)
                node = data.get('@graph', [data])[0] if isinstance(data, dict) else data[0]
                date_str = node.get('datePublished', '')
                m = re.search(r'(\d{2}:\d{2})', str(date_str))
                if m: return m.group(1)
            except: continue
    # General
    matches = re.findall(r'(\d{1,2}:\d{2})', texto)
    for m in matches:
        if m != ahora.strftime('%H:%M') and m != "04:00": return m
    return ""

def procesar_monitoreo():
    fuentes = [
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/"},
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/"},
        {"nombre": "UNITEL", "url": "https://unitel.bo/noticias/economia"},
        {"nombre": "RED UNO", "url": "https://www.reduno.com.bo/"},
        {"nombre": "ATB", "url": "https://www.atb.com.bo/"},
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/"},
