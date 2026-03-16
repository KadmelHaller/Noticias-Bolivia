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
    """Revisión de marcas de hora para mejorar la precisión"""
    texto = soup.get_text(" ", strip=True)
    
    # Intento 1: Metadatos de publicación (Muy efectivo en La Razón y Unitel)
    meta_time = soup.find("meta", property="article:published_time") or soup.find("meta", itemprop="datePublished")
    if meta_time:
        m = re.search(r'(\d{2}):(\d{2})', meta_time.get("content", ""))
        if m: return f"{m.group(1)}:{m.group(2)}"

    # Intento 2: JSON-LD
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

    # Intento 3: Selectores por medio
    if medio == "OPINIÓN":
        cuerpo = soup.find('article') or soup.find('div', class_='cuerpo')
        if cuerpo:
            m = re.search(r'(\d{1,2}:\d{2})', cuerpo.get_text())
            if m: return m.group(1)
    if medio == "LOS TIEMPOS":
        m = re.search(r'(\d{1,2})h(\d{2})', texto)
        if m: return f"{m.group(1)}:{m.group(2)}"
    
    # Intento 4: Búsqueda general de patrones HH:MM
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
        {"nombre": "URGENTE BO", "url": "https://www.urgente.bo/"},
        {"nombre": "IN NOTICIAS", "url": "https://innoticiasbo.com/"},
        {"nombre": "ENFOQUE NEWS", "url": "https://enfoquenews.com.bo/"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}
    data_final = ""
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
        st.write(f"📡 {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=15)
            if r.status_code != 200: continue
            
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            procesados, vistos = 0, set()
            
            for l in links:
                url_n = l['href']
                if not url_n.startswith('http'):
                    url_n = "https://larazon.bo" + url_n if "larazon" in fuente['url'] else fuente['url'].rstrip('/') + "/" + url_n.lstrip('/')
                
                texto_enlace = l.get_text().strip()
                if len(texto_enlace) < 20 or url_n in vistos or any(x in url_n for x in ['/tag/', '/autor/']): continue
                
                try:
                    rn = requests.get(url_n, headers=headers, timeout=10)
                    if rn.status_code != 200: continue
                    soup_n = BeautifulSoup(rn.text, 'html.parser')
                    h = extraer_hora_especifica(soup_n, fuente['nombre'])
                    cuerpo = " ".join([p.get_text().strip() for p in soup_n.find_all('p', limit=6) if len(p.get_text()) > 25])
                    
                    if len(cuerpo) > 150:
                        data_final +=
