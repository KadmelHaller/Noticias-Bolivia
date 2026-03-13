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
    if medio == "OPINIÓN":
        cuerpo = soup.find('article') or soup.find('div', class_='cuerpo')
        if cuerpo:
            m = re.search(r'(\d{1,2}:\d{2})', cuerpo.get_text())
            if m: return m.group(1)
    if medio == "LOS TIEMPOS":
        m = re.search(r'(\d{1,2})h(\d{2})', texto)
        if m: return f"{m.group(1)}:{m.group(2)}"
    if medio == "UNITEL":
        m_rel = re.search(r'hace\s+(\d+)\s+(minuto|hora)', texto.lower())
        if m_rel:
            cant = int(m_rel.group(1))
            delta = timedelta(minutes=cant) if 'min' in m_rel.group(2) else timedelta(hours=cant)
            return (ahora - delta).strftime('%H:%M')
    if medio in ["ATB", "IN NOTICIAS", "ENFOQUE NEWS", "LA RAZÓN", "LA RAZON"]:
        for s in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(s.string)
                node = data.get('@graph', [data])[0] if isinstance(data, dict) else data[0]
                date_str = node.get('datePublished', '')
                if date_str:
                    m = re.search(r'T(\d{2}):(\d{2})', date_str)
                    if m:
                        hh, mm = int(m.group(1)), m.group(2)
                        if medio == "ATB": hh = (hh - 4) % 24
                        return f"{hh:02d}:{mm}"
            except: continue
    matches = re.findall(r'(\d{1,2}:\d{2})', texto)
    for m in matches:
        if m != ahora.strftime('%H:%M') and m != "04:00": return m
    return ""

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
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'es-ES,es;q=0.9'
    }
    data_final = ""
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
        st.write(f"📡 {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=15)
            
            if r.status_code != 200:
                st.warning(f"⚠️ {fuente['nombre']} devolvió un código {r.status_code}. Saltando...")
                continue
                
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            procesados, vistos = 0, set()
            
            for l in links:
                url_n = l['href']
                # Construcción robusta de URL para La Razón
                if not url_n.startswith('http'):
                    url_n = "https://larazon.bo" + url_n if "larazon" in fuente['url'] else fuente['url'].rstrip('/') + "/" + url_n.lstrip('/')
                
                texto_enlace = l.get_text().strip()
                
                if len(texto_enlace) < 20 or url_n in vistos or '/tag/' in url_n or '/autor/' in url_n: 
                    continue
                
                try:
                    rn = requests.get(url_n, headers=headers, timeout=10)
                    if rn.status_code != 200: continue
                    
                    soup_n = BeautifulSoup(rn.text, 'html.parser')
                    h = extraer_hora_especifica(soup_n, fuente['nombre'])
                    cuerpo = " ".join([p.get_text().strip() for p in soup_n.find_all('p', limit=6) if len(p.get_text()) > 25])
                    
                    if len(cuerpo) > 150:
                        data_final += f"MEDIO: {fuente['nombre']} | HORA: {h} | TITULAR: {texto_enlace} | TXT: {cuerpo[:900]} | LINK: {url_n}\n\n"
                        vistos.add(url_n)
                        procesados += 1
                except: continue
                if procesados >= 5: break
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE FINAL'):
        raw_data = procesar_monitoreo()
        if len(raw_data) > 300:
            try:
                model = genai.GenerativeModel('models/gemini-flash-latest')
                prompt = f"""
                HOY ES: {fecha_hoy_bonita}.
                Extraer noticias de todos los medios detallados.
                Prioridad de temas: IMPUESTOS, ECONOMÍA y GOBIERNO BOLIVIANO.
                PRIORIDAD DE MEDIOS: OPINIÓN, LOS TIEMPOS, LA VOZ DE TARIJA, RESTO DE PERIÓDICOS, TELEVISIÓN, MEDIOS DIGITALES
                PRIORIDAD GEOGRÁFICA: 1. COCHABAMBA, 2. TARIJA, 3. Resto de Bolivia.
                
                Instrucción: Si hay noticias de Cochabamba o Tarija sobre los temas permitidos, ponlas al principio sin importar el medio.
                
                ESTRUCTURA:
                **TITULAR EN MAYÚSCULAS**
                **NOMBRE DEL MEDIO**
                **Hrs. HH:MM**
                Resumen detallado (4-6 líneas).
                URL directo, sin etiqueta
                """
                res = model.generate_content([prompt, raw_data])
                st.subheader("📋 Resumen Informativo:")
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {str(e)}")
