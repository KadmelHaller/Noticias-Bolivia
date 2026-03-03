import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import json

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")

# --- LÓGICA DE TIEMPO BOLIVIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_ref = ahora.strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO PROFUNDO: {fecha_ref}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_datos_articulo(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=8)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        hora_interna = ""
        metadatos_raw = ""

        # 1. JSON-LD
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    target = item.get('@graph', [item])
                    for node in target:
                        if 'datePublished' in node:
                            dt_match = re.search(r'(\d{2}:\d{2})', str(node['datePublished']))
                            if dt_match:
                                hora_interna = dt_match.group(1)
                                break
            except: continue
            if hora_interna: break

        # 2. Metatags
        meta_pub = soup.find("meta", property="article:published_time") or \
                   soup.find("meta", itemprop="datePublished") or \
                   soup.find("meta", name="publish-date")
        if meta_pub:
            metadatos_raw = meta_pub.get("content", "")

        parrafos = soup.find_all('p', limit=4)
        contenido = " ".join([p.get_text().strip() for p in parrafos])
        
        return hora_interna, metadatos_raw, contenido
    except:
        return "", "", ""

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
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    data_raw = ""
    pb = st.progress(0)
    st_info = st.empty()
    
    for i, fuente in enumerate(fuentes):
        st_info.text(f"Scrapeando: {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            articulos = soup.find_all(['h1', 'h2', 'h3'], limit=7)
            
            for art in articulos:
                a_tag = art.find('a') or art.find_parent('a')
                if a_tag and a_tag.get('href'):
                    full_link = a_tag['href'] if a_tag['href'].startswith('http') else fuente['base'].rstrip('/') + a_tag['href']
                    h_int, m_raw, txt = extraer_datos_articulo(full_link, headers)
                    
                    if len(txt) > 100:
                        data_raw += f"ORDEN: {i+1} | MEDIO: {fuente['nombre']} | HORA_INT: {h_int} | META: {m_raw} | TEMA: {art.get_text().strip()} | LINK: {full_link} | TXT: {txt[:600]}\n"
        except: continue
    
    pb.empty()
    st_info.empty()
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR MONITOREO PROFUNDO'):
        raw_data = extraer_noticias()
        if len(raw_data) > 300:
            try:
                # --- DETECCIÓN AUTOMÁTICA DEL MODELO ---
                modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # Priorizar flash 1.5, si no usar el primero que funcione
                modelo_final = next((m for m in modelos_disponibles if "1.5-flash" in m), modelos_disponibles[0])
                
                model = genai.GenerativeModel(modelo_final)
                
                prompt = f"""
                FECHA: {fecha_ref}. HORA ACTUAL BOLIVIA: {ahora.strftime('%H:%M')}.
                TAREA: Monitoreo de prensa técnico.
                FILTRADO: ELIMINA Deportes, Farándula e Internacional.
                PRIORIZA: Economía, Impuestos, Gobierno de Cochabamba y Tarija.
                ORDENA: Según 'ORDEN' de la fuente (1 al 12).

                JERARQUÍA DE HORA:
                1. 'HORA_INT' (HH:MM).
                2. 'LINK' (patrón de 4 dígitos tras fecha).
                3. 'META'.
                4. Estima y pon "(aprox.)".

                FORMATO SALIDA:
                *TITULAR EN MAYÚSCULAS Y NEGRITA*
                MEDIO EN MAYÚSCULAS Y NEGRITA
                HH:MM (Solo números)
                Resumen de 4 a 6 líneas.
                URL

                ENTRADA:
                {raw_data}
                """
                
                with st.spinner(f"Usando {modelo_final}..."):
                    res = model.generate_content(prompt)
                
                if res.text:
                    st.subheader("📋 Resultado Final:")
                    processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                    st.markdown(f'<div style="font-family:serif; font-size:13px; text-align:justify; background:white; color:black; padding:20px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            
            except Exception as e:
                st.error(f"Error técnico: {str(e)}")
        else:
            st.warning("No se obtuvo suficiente información. Intenta de nuevo.")
