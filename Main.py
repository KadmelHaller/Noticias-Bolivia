import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import json
import time

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")

# --- LÓGICA DE TIEMPO BOLIVIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_ref = ahora.strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO TOTAL: {fecha_ref}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_datos_articulo(url, headers):
    try:
        # Reintento para estabilidad
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        hora_detectada = ""

        # 1. PATRÓN LOS TIEMPOS (##h##) Y ESTÁNDAR (##:##)
        texto_pagina = soup.get_text()
        
        # Primero buscamos el formato de Los Tiempos: 13h55
        match_lt = re.search(r'(\d{1,2})h(\d{2})', texto_pagina)
        if match_lt:
            hora_detectada = f"{match_lt.group(1)}:{match_lt.group(2)}"
        
        # Si no, buscamos formato estándar 13:55
        if not hora_detectada:
            match_std = re.search(r'(\d{1,2}:\d{2})', texto_pagina)
            if match_std:
                hora_detectada = match_std.group(1)

        # 2. JSON-LD (Respaldo técnico)
        if not hora_detectada:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        graph = item.get('@graph', [item])
                        for node in graph:
                            if 'datePublished' in node:
                                m = re.search(r'(\d{2}:\d{2})', str(node['datePublished']))
                                if m: 
                                    hora_detectada = m.group(1)
                                    break
                except: continue

        # EXTRAER TEXTO (Filtro mínimo de 80 caracteres para Tarija)
        parrafos = soup.find_all('p', limit=6)
        contenido = " ".join([p.get_text().strip() for p in parrafos])
        if len(contenido) < 80: return None, None
        
        return hora_detectada, contenido
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
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    data_raw = ""
    pb = st.progress(0)
    info_st = st.empty()
    
    for i, fuente in enumerate(fuentes):
        info_st.text(f"Analizando: {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Buscamos artículos específicamente en La Voz de Tarija (usan article)
            tags_noticias = soup.find_all(['h1', 'h2', 'h3', 'article'], limit=12)
            
            procesados = 0
            for tag in tags_noticias:
                if procesados >= 8: break
                
                a_tag = tag.find('a', href=True) if tag.name != 'a' else tag
                if a_tag:
                    url_n = a_tag['href']
                    full_link = url_n if url_n.startswith('http') else fuente['base'].rstrip('/') + url_n
                    
                    # Evitar secciones basura
                    if any(x in full_link.lower() for x in ['/category/', '/tag/', '/author/']): continue
                    
                    h_res, t_res = extraer_datos_articulo(full_link, headers)
                    
                    if t_res:
                        data_raw += f"ID: {i+1} | MEDIO: {fuente['nombre']} | HORA_DOC: {h_res} | TEMA: {a_tag.get_text().strip()} | LINK: {full_link} | TXT: {t_res[:750]}\n"
                        procesados += 1
        except: continue
    
    info_st.empty()
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 EJECUTAR MONITOREO'):
        raw_data = extraer_noticias()
        if len(raw_data) > 300:
            modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model = genai.GenerativeModel(next((m for m in modelos if "1.5-flash" in m), modelos[0]))
            
            prompt = f"""
            HOY ES: {fecha_ref}. HORA ACTUAL: {ahora.strftime('%H:%M')}.
            
            FILTRADO:
            - Solo Economía, Gobierno, Impuestos, Aduana o gestión municipal.
            - ELIMINA Deportes, Farándula e Internacional.
            - PRIORIZA Cochabamba y Tarija.

            REGLA DE HORA:
            - Si 'HORA_DOC' tiene un valor (ej. 13:55), USALO SIEMPRE. Es la prioridad.
            - Solo si está vacío, pon una hora estimada lógica de hoy con "(aprox.)".

            FORMATO DE SALIDA:
            Agrupa por MEDIO siguiendo el orden del ID (1 al 12).
            *TITULAR EN MAYÚSCULAS Y NEGRITA*
            MEDIO EN MAYÚSCULAS Y NEGRITA
            HH:MM
            Párrafo detallado (4-6 líneas).
            URL

            DATOS:
            {raw_data}
            """
            with st.spinner("IA generando reporte final..."):
                res = model.generate_content(prompt)
            
            if res.text:
                st.subheader("📋 Monitoreo de Prensa:")
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
