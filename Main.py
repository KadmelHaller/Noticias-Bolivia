import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import json

st.set_page_config(page_title="Monitoreo Bolivia Especializado", page_icon="🇧🇴", layout="wide")

# --- CONFIGURACIÓN DE TIEMPO BOLIVIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO TÉCNICO DE PRENSA: {fecha_hoy_bonita}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_hora_especifica(soup, medio, url):
    texto_completo = soup.get_text(" ", strip=True)
    
    # 1. OPINIÓN: Ignorar encabezado, buscar en el cuerpo
    if medio == "OPINIÓN":
        cuerpo = soup.find('article') or soup.find('div', class_='cuerpo')
        if cuerpo:
            m = re.search(r'(\d{1,2}:\d{2})', cuerpo.get_text())
            if m: return m.group(1)

    # 2. LOS TIEMPOS: Formato 13h55 -> 13:55
    if medio == "LOS TIEMPOS":
        m = re.search(r'(\d{1,2})h(\d{2})', texto_completo)
        if m: return f"{m.group(1)}:{m.group(2)}"

    # 5. UNITEL: Calcular hora desde "hace x minutos/horas"
    if medio == "UNITEL":
        m_rel = re.search(r'hace\s+(\d+)\s+(minuto|hora)', texto_completo.lower())
        if m_rel:
            cant = int(m_rel.group(1))
            delta = timedelta(minutes=cant) if 'min' in m_rel.group(2) else timedelta(hours=cant)
            return (ahora - delta).strftime('%H:%M')

    # 4, 11, 12. METADATOS (ATB, In Noticias, Enfoque News)
    if medio in ["ATB", "IN NOTICIAS", "ENFOQUE NEWS"]:
        scripts = soup.find_all('script', type='application/ld+json')
        for s in scripts:
            try:
                data = json.loads(s.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    node = item.get('@graph', [item])[0]
                    date_str = node.get('datePublished', '')
                    m = re.search(r'(\d{2}:\d{2})', str(date_str))
                    if m: return m.group(1)
            except: continue

    # 3, 6, 7, 8, 10. Búsqueda directa en artículo (Tarija, Red Uno, BTV, Bolivisión, Urgente)
    # Buscamos patrones HH:MM que no sean la hora actual (reloj del sitio)
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
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
        st.write(f"📡 Procesando {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            procesados = 0
            vistos = set()
            
            for l in links:
                url_n = l['href']
                if not url_n.startswith('http'):
                    base = fuente['url'].split('.bo')[0] + '.bo' if '.bo' in fuente['url'] else fuente['url'].rstrip('/')
                    url_n = base + ('' if url_n.startswith('/') else '/') + url_n
                
                if len(l.get_text().strip()) < 35 or url_n in vistos or any(x in url_n for x in ['/tag/', '/category/']):
                    continue
                
                # Entrar a la noticia
                try:
                    rn = requests.get(url_n, headers=headers, timeout=10)
                    soup_n = BeautifulSoup(rn.text, 'html.parser')
                    
                    hora = extraer_hora_especifica(soup_n, fuente['nombre'], url_n)
                    
                    # Extraer cuerpo
                    parrafos = soup_n.find_all('p', limit=6)
                    cuerpo = " ".join([p.get_text().strip() for p in parrafos if len(p.get_text()) > 30])
                    
                    if len(cuerpo) > 150:
                        data_final += f"MEDIO: {fuente['nombre']} | HORA: {hora} | TITULAR: {l.get_text().strip()} | LINK: {url_n} | TXT: {cuerpo[:800]}\n\n"
                        vistos.add(url_n)
                        procesados += 1
                except: continue
                
                if procesados >= 5: break
        except: continue
            
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE DEFINITIVO'):
        noticias_raw = procesar_monitoreo()
        
        if len(noticias_raw) > 500:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            HOY ES: {fecha_hoy_bonita}.
            
            INSTRUCCIONES:
            - Solo incluye noticias de Economía, Gobierno, Aduana, Impuestos y Gestión Municipal.
            - ELIMINA Deportes, Farándula, Policiales e Internacional.
            - Usa OBLIGATORIAMENTE la hora proporcionada en 'HORA'. 
            - Si 'HORA' está vacío, estima la hora basándote en que es una noticia de hoy ({fecha_hoy_bonita}) y pon "(aprox.)".
            
            FORMATO:
            - Lista continua (sin nombres de medios como separadores).
            *TITULAR EN MAYÚSCULAS Y NEGRITA*
            MEDIO EN MAYÚSCULAS Y NEGRITA
            HH:MM
            Resumen detallado de 4 a 6 líneas.
            URL
            """
            
            res = model.generate_content([prompt, noticias_raw])
            
            if res.text:
                st.subheader("📋 Resultado:")
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
