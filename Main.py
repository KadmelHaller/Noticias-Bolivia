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
        # Reintento para sitios difíciles
        for _ in range(2):
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200: break
            time.sleep(1)
            
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        hora_detectada = ""

        # ESTRATEGIA 1: Buscar texto con formato HH:MM en el cuerpo (Muy efectivo para Opinión/Tarija)
        # Buscamos en las primeras etiquetas de la nota
        elementos_fecha = soup.find_all(['span', 'div', 'time', 'p'], limit=15)
        for el in elementos_fecha:
            txt = el.get_text().strip()
            # Patrón de hora: 10:59, 11:08, etc.
            match = re.search(r'(\d{1,2}:\d{2})', txt)
            if match:
                hora_detectada = match.group(1)
                break

        # ESTRATEGIA 2: JSON-LD (Si la 1 falla)
        if not hora_detectada:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        target = item.get('@graph', [item])
                        for node in target:
                            if 'datePublished' in node:
                                m = re.search(r'(\d{2}:\d{2})', str(node['datePublished']))
                                if m: 
                                    hora_detectada = m.group(1)
                                    break
                except: continue

        # ESTRATEGIA 3: Tiempo relativo
        if not hora_detectada:
            rel_match = re.search(r'hace\s+(\d+)\s+(minuto|hora)', soup.get_text().lower())
            if rel_match:
                cant = int(rel_match.group(1))
                dt = ahora - (timedelta(minutes=cant) if 'min' in rel_match.group(2) else timedelta(hours=cant))
                hora_detectada = dt.strftime('%H:%M')

        # EXTRAER TEXTO (Bajamos el límite a 100 para que entren notas cortas de Tarija)
        parrafos = soup.find_all('p', limit=6)
        contenido = " ".join([p.get_text().strip() for p in parrafos])
        if len(contenido) < 100: return None, None
        
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
        info_st.text(f"Conectando con {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            # Buscamos más links para asegurar que no se pierdan noticias
            links_encontrados = soup.find_all('a', href=True)
            
            procesados = 0
            for link in links_encontrados:
                if procesados >= 8: break # Límite por medio
                
                url_n = link['href']
                if url_n.startswith('/') or fuente['base'] in url_n:
                    full_link = url_n if url_n.startswith('http') else fuente['base'].rstrip('/') + url_n
                    
                    # Filtro básico de URL para evitar secciones
                    if any(x in full_link for x in ['/category/', '/tag/', '/author/', '/page/']): continue
                    
                    h_res, t_res = extraer_datos_articulo(full_link, headers)
                    
                    if t_res and len(link.get_text()) > 25:
                        data_raw += f"ID: {i+1} | MEDIO: {fuente['nombre']} | HORA_DOC: {h_res} | TEMA: {link.get_text().strip()} | LINK: {full_link} | TXT: {t_res[:700]}\n"
                        procesados += 1
        except: continue
    info_st.empty()
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 EJECUTAR MONITOREO COMPLETO'):
        raw_data = extraer_noticias()
        if len(raw_data) > 300:
            modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model = genai.GenerativeModel(next((m for m in modelos if "1.5-flash" in m), modelos[0]))
            
            prompt = f"""
            HOY ES: {fecha_ref}. HORA ACTUAL: {ahora.strftime('%H:%M')}.
            
            INSTRUCCIONES DE FILTRADO:
            - SOLO quédate con noticias de Economía, Gobierno, Impuestos o gestión municipal.
            - ELIMINA TODO lo referente a Deportes, Farándula, Sucesos Policiales menores o Internacional.
            - PRIORIZA Cochabamba y Tarija.

            INSTRUCCIONES DE HORA:
            - SI 'HORA_DOC' tiene una hora (ej. 10:59), ÚSALA OBLIGATORIAMENTE. No pongas "(aprox.)" si hay un dato en 'HORA_DOC'.
            - Si 'HORA_DOC' está vacío, estima la hora basándote en el 'LINK' o el contexto de "noticia de hoy" y pon "(aprox.)".

            FORMATO DE SALIDA:
            Agrupa por MEDIO siguiendo el orden del ID (1 al 12).
            *TITULAR EN MAYÚSCULAS Y NEGRITA*
            MEDIO EN MAYÚSCULAS Y NEGRITA
            HH:MM
            Resumen informativo detallado (4-6 líneas).
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
