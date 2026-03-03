import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import json

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")

# --- LÓGICA DE TIEMPO BOLIVIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_ref = ahora.strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO FINAL: {fecha_ref}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def calcular_hora_relativa(texto):
    texto = texto.lower()
    try:
        match = re.search(r'(\d+)\s+(minuto|hora)', texto)
        if match:
            cantidad = int(match.group(1))
            unidad = match.group(2)
            dt = ahora - (timedelta(minutes=cantidad) if 'minuto' in unidad else timedelta(hours=cantidad))
            return dt.strftime('%H:%M')
    except: pass
    return None

def extraer_datos_articulo(url, headers):
    # Evitar links basura de navegación
    if any(x in url.lower() for x in ['/category/', '/tag/', '/author/', '/page/', '/seccion/']):
        return None, None

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        hora_final = ""

        # 1. NIVEL 1: JSON-LD (Metadatos técnicos)
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    graph = item.get('@graph', [item])
                    for node in graph:
                        if 'datePublished' in node:
                            raw_date = node['datePublished']
                            match = re.search(r'(\d{2}):(\d{2})', raw_date)
                            if match:
                                hh, mm = int(match.group(1)), match.group(2)
                                # Solo ajustar si es explícitamente UTC y la hora resultaría lógica
                                if 'Z' in raw_date or '+00' in raw_date:
                                    hh = (hh - 4) % 24
                                if not (hh == 4 and mm == "00"): # Evitar el bug del 04:00
                                    hora_final = f"{hh:02d}:{mm}"
                                    break
            except: continue
            if hora_final: break

        # 2. NIVEL 2: TIEMPO RELATIVO (Fundamental para UNITEL)
        if not hora_final:
            for tag in soup.find_all(['span', 'div', 'time']):
                rel = calcular_hora_relativa(tag.get_text())
                if rel:
                    hora_final = rel
                    break

        # 3. EXTRAER CONTENIDO
        parrafos = soup.find_all('p', limit=5)
        contenido = " ".join([p.get_text().strip() for p in parrafos])
        if len(contenido) < 200: return None, None # Ignorar páginas vacías o de error
        
        return hora_final, contenido
    except:
        return None, None

def extraer_noticias():
    fuentes = [
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/", "base": "https://www.opinion.com.bo"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/", "base": "https://www.lostiempos.com"},
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/", "base": "https://lavozdetarija.com"},
        {"nombre": "UNITEL", "url": "https://unitel.bo/", "base": "https://unitel.bo"},
        {"nombre": "RED UNO", "url": "https://www.reduno.com.bo/", "base": "https://www.reduno.com.bo"},
        {"nombre": "ATB", "url": "https://www.atb.com.bo/", "base": "https://www.atb.com.bo"},
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/", "base": "https://www.boliviatv.bo"},
        {"nombre": "BOLIVISION", "url": "https://www.redbolivision.tv.bo/", "base": "https://www.redbolivision.tv.bo"},
        {"nombre": "CADENA A", "url": "https://www.cadenaa.tv/", "base": "https://www.cadenaa.tv"},
        {"nombre": "URGENTE BO", "url": "https://www.urgente.bo/", "base": "https://www.urgente.bo"},
        {"nombre": "IN NOTICIAS", "url": "https://innoticiasbo.com/", "base": "https://innoticiasbo.com"},
        {"nombre": "ENFOQUE NEWS", "url": "https://enfoquenews.com.bo/", "base": "https://enfoquenews.com.bo"}
    ]
    
    # User-Agent más "humano" para evitar bloqueos de Los Tiempos
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    data_raw = ""
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            articulos = soup.find_all(['h1', 'h2', 'h3'], limit=10)
            
            for art in articulos:
                a_tag = art.find('a') or art.find_parent('a')
                if a_tag and a_tag.get('href'):
                    full_link = a_tag['href'] if a_tag['href'].startswith('http') else fuente['base'].rstrip('/') + a_tag['href']
                    h_real, txt = extraer_datos_articulo(full_link, headers)
                    
                    if txt:
                        data_raw += f"ID_MEDIO: {i+1} | MEDIO: {fuente['nombre']} | HORA_DOC: {h_real} | LINK: {full_link} | TEXTO: {txt[:700]}\n"
        except: continue
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR MONITOREO LIMPIO'):
        raw_data = extraer_noticias()
        if len(raw_data) > 300:
            modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model = genai.GenerativeModel(next((m for m in modelos if "1.5-flash" in m), modelos[0]))
            
            prompt = f"""
            HOY ES: {fecha_ref}. HORA ACTUAL BOLIVIA: {ahora.strftime('%H:%M')}.
            
            REGLAS:
            1. FILTRADO: ELIMINA Deportes, Farándula, Internacional y páginas de error/portada.
            2. PRIORIZA: Economía, Gobierno, Cochabamba y Tarija.
            3. ORDEN: Agrupa por 'MEDIO' siguiendo el orden de 'ID_MEDIO' (1 al 12). No escribas "ORDEN: ##" en el resultado.
            
            REGLA DE HORA:
            - Usa 'HORA_DOC'. Si es "04:00" y la noticia es reciente, ignórala y pon la hora actual aprox. o busca en el LINK.
            - Si no hay hora, pon una hora lógica de hoy y añade "(aprox.)".

            FORMATO DE SALIDA (ESTRICTO):
            *TITULAR EN MAYÚSCULAS Y NEGRITA*
            MEDIO EN MAYÚSCULAS Y NEGRITA
            HH:MM
            Párrafo de 4-6 líneas detallado.
            URL

            DATOS: {raw_data}
            """
            res = model.generate_content(prompt)
            if res.text:
                st.subheader("📋 Informe Final:")
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:20px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
