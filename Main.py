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
    
    # 1. OPINIÓN
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
 
    # 4. ATB (Corrección UTC -4) y otros metadatos
    if medio in ["ATB", "IN NOTICIAS", "ENFOQUE NEWS", "LA RAZÓN"]:
        for s in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(s.string)
                node = data.get('@graph', [data])[0] if isinstance(data, dict) else data[0]
                date_str = node.get('datePublished', '')
                if date_str:
                    m = re.search(r'T(\d{2}):(\d{2})', date_str)
                    if m:
                        hh, mm = int(m.group(1)), m.group(2)
                        if medio == "ATB": # Solo aplicamos resta a ATB
                            hh = (hh - 4) % 24
                        return f"{hh:02d}:{mm}"
            except: continue

    # General para el resto
    matches = re.findall(r'(\d{1,2}:\d{2})', texto)
    for m in matches:
        if m != ahora.strftime('%H:%M') and m != "04:00": return m
    return ""

def procesar_monitoreo():
    fuentes = [
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/"},
        {"nombre": "LA RAZÓN", "url": "https://larazon.bo/"},
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
        st.write(f"📡 {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            procesados, vistos = 0, set()
            for l in links:
                url_n = l['href']
                if not url_n.startswith('http'):
                    base = fuente['url'].split('.bo')[0] + '.bo' if '.bo' in fuente['url'] else fuente['url'].rstrip('/')
                    url_n = base + ('' if url_n.startswith('/') else '/') + url_n
                if len(l.get_text().strip()) < 35 or url_n in vistos or any(x in url_n for x in ['/tag/', '/category/']): continue
                try:
                    rn = requests.get(url_n, headers=headers, timeout=10)
                    soup_n = BeautifulSoup(rn.text, 'html.parser')
                    h = extraer_hora_especifica(soup_n, fuente['nombre'])
                    cuerpo = " ".join([p.get_text().strip() for p in soup_n.find_all('p', limit=6) if len(p.get_text()) > 25])
                    if len(cuerpo) > 150:
                        data_final += f"MEDIO: {fuente['nombre']} | HORA: {h} | TITULAR: {l.get_text().strip()} | TXT: {cuerpo[:900]} | LINK: {url_n}\n\n"
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
                REGLAS DE FILTRADO: Economía, Gobierno, Impuestos. EXCLUIR TODO LO DEMÁS.
                REGLA DE HORA: Usa 'HORA'. Si está vacía, pon "Sin hora en datos y metadatos".
                REGLA DE MEDIOS: PRIORIZA "OPINIÓN", "LOS TIEMPOS" Y "LA VOZ DE TARIJA".
                
                ESTRUCTURA OBLIGATORIA (CON SALTOS DE LÍNEA):
                **TITULAR EN MAYÚSCULAS**
                **NOMBRE DEL MEDIO**
                **Hrs. HH:MM**
                Resumen detallado de 4 a 6 líneas.
                URL
                
                No agrupar por medio. Lista continua.
                """
                res = model.generate_content([prompt, raw_data])
                st.subheader("📋 Resumen Informativo:")
                # Convertimos negrillas de Markdown a HTML para el contenedor
                processed = res.text.replace("**", "<b>").replace("**", "</b>")
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {str(e)}")
