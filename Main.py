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

def extraer_datos_articulo(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        hora_final = ""

        # --- NIVEL 1: METADATOS TÉCNICOS (La Voz de Tarija, Opinión, etc.) ---
        # Buscamos en JSON-LD el campo datePublished
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    graph = item.get('@graph', [item])
                    for node in graph:
                        if 'datePublished' in node:
                            raw_date = node['datePublished'] # Ejemplo: 2026-03-03T11:08:45+00:00
                            match = re.search(r'(\d{2}):(\d{2})', raw_date)
                            if match:
                                hh, mm = int(match.group(1)), match.group(2)
                                # Ajuste de UTC a BOT (Bolivia Time -4) si detectamos Z o +00
                                if 'Z' in raw_date or '+00' in raw_date:
                                    hh = (hh - 4) % 24
                                hora_final = f"{hh:02d}:{mm}"
                                break
                    if hora_final: break
            except: continue
            if hora_final: break

        # --- NIVEL 2: TIEMPO RELATIVO (Unitel) ---
        if not hora_final:
            texto_completo = soup.get_text().lower()
            # Buscamos patrones como "hace 5 minutos" o "hace 1 hora"
            rel_match = re.search(r'hace\s+(\d+)\s+(minuto|hora)', texto_completo)
            if rel_match:
                cantidad = int(rel_match.group(1))
                unidad = rel_match.group(2)
                if 'minuto' in unidad:
                    dt = ahora - timedelta(minutes=cantidad)
                else:
                    dt = ahora - timedelta(hours=cantidad)
                hora_final = dt.strftime('%H:%M')

        # --- NIVEL 3: ETIQUETAS HTML VISIBLES ---
        if not hora_final:
            tag_t = soup.find(['time']) or soup.find(class_=re.compile(r'entry-date|published|fecha', re.I))
            if tag_t:
                content = tag_t.get('content') or tag_t.get_text()
                match = re.search(r'(\d{2}):(\d{2})', str(content))
                if match:
                    hora_final = match.group(0)

        # EXTRAER TEXTO
        parrafos = soup.find_all('p', limit=5)
        contenido = " ".join([p.get_text().strip() for p in parrafos])
        
        return hora_final, contenido
    except:
        return "", ""

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
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    data_raw = ""
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            articulos = soup.find_all(['h1', 'h2', 'h3'], limit=8)
            
            for art in articulos:
                a_tag = art.find('a') or art.find_parent('a')
                if a_tag and a_tag.get('href'):
                    full_link = a_tag['href'] if a_tag['href'].startswith('http') else fuente['base'].rstrip('/') + a_tag['href']
                    h_real, txt = extraer_datos_articulo(full_link, headers)
                    
                    if len(txt) > 150:
                        data_raw += f"ORDEN: {i+1} | MEDIO: {fuente['nombre']} | HORA_REAL: {h_real} | LINK: {full_link} | TXT: {txt[:700]}\n"
        except: continue
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR MONITOREO'):
        raw_data = extraer_noticias()
        if len(raw_data) > 300:
            modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            modelo_final = next((m for m in modelos if "1.5-flash" in m), modelos[0])
            model = genai.GenerativeModel(modelo_final)
            
            prompt = f"""
            HOY ES: {fecha_ref}. HORA ACTUAL BOLIVIA: {ahora.strftime('%H:%M')}.
            TAREA: Monitoreo técnico de prensa.
            FILTRADO ESTRICTO: ELIMINA Deportes, Farándula e Internacional.
            PRIORIZA: Economía, Impuestos, Gobierno de Cochabamba y Tarija.
            ORDENA: Según 'ORDEN' (1 al 12).

            REGLA DE HORA (CRÍTICA):
            1. Si 'HORA_REAL' tiene un valor HH:MM, ÚSALO SIN CAMBIOS. Es el dato extraído del código fuente.
            2. Si 'HORA_REAL' está vacío, busca la hora en el 'LINK' (ej. 1310).
            3. Solo si no hay rastro, estima y pon "(aprox.)".

            FORMATO:
            *TITULAR EN MAYÚSCULAS Y NEGRITA*
            MEDIO EN MAYÚSCULAS Y NEGRITA
            HH:MM
            Párrafo de 4-6 líneas detallado.
            URL

            DATOS: {raw_data}
            """
            res = model.generate_content(prompt)
            if res.text:
                st.subheader("📋 Resultado Final:")
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:20px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
