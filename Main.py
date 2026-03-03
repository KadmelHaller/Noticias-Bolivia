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

    matches = re.findall(r'(\d{1,2}:\d{2})', texto)
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
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
        st.write(f"📡 Explorando {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.select('article a[href]') if fuente['nombre'] == "LA VOZ DE TARIJA" else soup.find_all('a', href=True)

            procesados = 0
            vistos = set()
            for l in links:
                url_n = l['href']
                if not url_n.startswith('http'):
                    base = fuente['url'].split('.bo')[0] + '.bo' if '.bo' in fuente['url'] else fuente['url'].rstrip('/')
                    url_n = base + ('' if url_n.startswith('/') else '/') + url_n
                
                if len(l.get_text().strip()) < 30 or url_n in vistos or any(x in url_n for x in ['/tag/', '/category/']):
                    continue
                
                try:
                    rn = requests.get(url_n, headers=headers, timeout=10)
                    soup_n = BeautifulSoup(rn.text, 'html.parser')
                    h = extraer_hora_especifica(soup_n, fuente['nombre'])
                    cuerpo = " ".join([p.get_text().strip() for p in soup_n.find_all('p', limit=6) if len(p.get_text()) > 25])
                    if len(cuerpo) > 120:
                        data_final += f"MEDIO: {fuente['nombre']} | HORA: {h} | TITULAR: {l.get_text().strip()} | LINK: {url_n} | TXT: {cuerpo[:800]}\n\n"
                        vistos.add(url_n)
                        procesados += 1
                except: continue
                if procesados >= 5: break
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE'):
        raw_data = procesar_monitoreo()
        if len(raw_data) > 300:
            # --- DETECCIÓN DINÁMICA DE MODELO ---
            try:
                modelos_visibles = genai.list_models()
                nombre_modelo = next(m.name for m in modelos_visibles if '1.5-flash' in m.name)
                model = genai.GenerativeModel(nombre_modelo)
            except:
                model = genai.GenerativeModel('gemini-1.5-flash-latest') # Fallback
            
            prompt = f"""
            HOY ES: {fecha_hoy_bonita}.
            FILTRO: Solo Economía, Gobierno, Aduana, Impuestos y Gestión Municipal.
            ELIMINA: Deportes, Farándula, Policiales e Internacional.
            HORA: Usa 'HORA'. Si no hay, pon una de hoy con "(aprox.)".
            FORMATO: Lista continua, *TITULAR*, MEDIO, HH:MM, Resumen (4-6 líneas), URL.
            """
            
            try:
                res = model.generate_content([prompt, raw_data])
                st.subheader("📋 Resultado:")
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error de Generación: {str(e)}")
