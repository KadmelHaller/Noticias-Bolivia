import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import json
import time

st.set_page_config(page_title="Monitoreo Bolivia Pro", page_icon="🇧🇴", layout="wide")

# --- CONFIGURACIÓN DE TIEMPO BOLIVIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO TÉCNICO DE PRENSA: {fecha_hoy_bonita}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_hora_especifica(soup, medio, url):
    texto_completo = soup.get_text(" ", strip=True)
    
    # 1. OPINIÓN: Buscar específicamente en la zona del artículo
    if medio == "OPINIÓN":
        cuerpo = soup.find('article') or soup.find('div', class_='cuerpo')
        if cuerpo:
            m = re.search(r'(\d{1,2}:\d{2})', cuerpo.get_text())
            if m: return m.group(1)

    # 2. LOS TIEMPOS: Formato 13h55 -> 13:55
    if medio == "LOS TIEMPOS":
        m = re.search(r'(\d{1,2})h(\d{2})', texto_completo)
        if m: return f"{m.group(1)}:{m.group(2)}"

    # 5. UNITEL: Calcular desde relativo
    if medio == "UNITEL":
        m_rel = re.search(r'hace\s+(\d+)\s+(minuto|hora)', texto_completo.lower())
        if m_rel:
            cant = int(m_rel.group(1))
            delta = timedelta(minutes=cant) if 'min' in m_rel.group(2) else timedelta(hours=cant)
            return (ahora - delta).strftime('%H:%M')

    # 4, 11, 12. METADATOS (ATB, IN NOTICIAS, ENFOQUE)
    if medio in ["ATB", "IN NOTICIAS", "ENFOQUE NEWS"]:
        for s in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(s.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    graph = item.get('@graph', [item])
                    for node in graph:
                        date_str = node.get('datePublished', '')
                        m = re.search(r'(\d{2}:\d{2})', str(date_str))
                        if m: return m.group(1)
            except: continue

    # 3, 6, 7, 8, 10. Búsqueda directa (Tarija, Red Uno, BTV, Bolivisión, Urgente)
    matches = re.findall(r'(\d{1,2}:\d{2})', texto_completo)
    for m in matches:
        if m != ahora.strftime('%H:%M') and m != "04:00":
            return m
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
        {"nombre": "BOLIVISION", "url": "https://www.redbolivision.tv.bo/"},
        {"nombre": "URGENTE BO", "url": "https://www.urgente.bo/"},
        {"nombre": "IN NOTICIAS", "url": "https://innoticiasbo.com/"},
        {"nombre": "ENFOQUE NEWS", "url": "https://enfoquenews.com.bo/"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
    data_final = ""
    pb = st.
