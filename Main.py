import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import time

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")

# --- LÓGICA DE TIEMPO BOLIVIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_ref = ahora.strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO FINAL: {fecha_ref}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_datos_articulo(url, headers):
    try:
        # Reintento con espera para evitar bloqueos
        time.sleep(0.5)
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Eliminar scripts y estilos para limpiar el texto
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
            
        texto_limpio = soup.get_text(" ", strip=True)
        # Tomamos solo el inicio de la página para buscar la hora (donde suele estar)
        fragmento_inicio = texto_limpio[:2000] 
        
        hora_detectada = ""

        # 1. BUSCAR FORMATO LOS TIEMPOS (13h55)
        match_lt = re.search(r'(\d{1,2})h(\d{2})', fragmento_inicio)
        if match_lt:
            hora_detectada = f"{match_lt.group(1)}:{match_lt.group(2)}"
        
        # 2. BUSCAR FORMATO ESTÁNDAR (11:08) - Excluyendo el bug del 04:00 si es posible
        if not hora_detectada:
            matches_std = re.findall(r'(\d{1,2}:\d{2})', fragmento_inicio)
            for m in matches_std:
                if m != "04:00": # Filtro manual contra el bug de Unitel
                    hora_detectada = m
                    break

        # 3. TIEMPO RELATIVO (Para Unitel)
        if not hora_detectada or hora_detectada == "04:00":
            rel_match = re.search(r'hace\s+(\d+)\s+(minuto|hora)', fragmento_inicio.lower())
            if rel_match:
                cant = int(rel_match.group(1))
                dt = ahora - (timedelta(minutes=cant) if 'min' in rel_match.group(2) else timedelta(hours=cant))
                hora_detectada = dt.strftime('%H:%M')

        # EXTRAER CONTENIDO
        parrafos = soup.find_all('p', limit=6)
        contenido = " ".join([p.get_text().strip() for p in parrafos])
        
        # Si no hay párrafos, buscamos divs con mucho texto (algunos medios no usan <p>)
        if len(contenido) < 100:
            divs = soup.find_all('div', limit=10)
            contenido = " ".join([d.get_text().strip() for d in divs if len(d.get_text()) > 100][:2])

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
    
    # Headers mucho más completos para evitar bloqueos
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    data_raw = ""
    pb = st.progress(0)
    info_st = st.empty()
    
    for i, fuente in enumerate(fuentes):
        info_st.text(f"Accediendo a {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Buscamos todos los links que parezcan noticias (más de 30 caracteres de texto)
            links = soup.find_all('a', href=True)
            
            procesados = 0
            enlaces_vistos = set()

            for l in links:
                if procesados >= 10: break
                
                texto_link = l.get_text().strip()
                url_n = l['href']
                
                if len(texto_link) < 35: continue # Ignorar links cortos (menú, etc)
                
                full_link = url_n if url_n.startswith('http') else fuente['base'].rstrip('/') + url_n
                if full_link in enlaces_vistos: continue
                
                # Filtro agresivo de URL
                if any(x in full_link.lower() for x in ['/category/', '/tag/', '/author/', 'whatsapp', 'facebook', 'twitter']): continue
                
                h_res, t_res = extraer_datos_articulo(full_link, headers)
                
                if t_res and len(t_res) > 150:
                    enlaces_vistos.add(full_link)
                    data_raw += f"ID: {i+1} | MEDIO: {fuente['nombre']} | HORA_DOC: {h_res} | TEMA: {texto_link} | LINK: {full_link} | TXT: {t_res[:800]}\n"
                    procesados += 1
                    
        except: continue
    
    info_st.empty()
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 INICIAR MONITOREO DE ALTA PRECISIÓN'):
        raw_data = extraer_noticias()
        if len(raw_data) > 300:
            modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model = genai.GenerativeModel(next((m for m in modelos if "1.5-flash" in m), modelos[0]))
            
            prompt = f"""
            HOY ES: {fecha_ref}. HORA ACTUAL: {ahora.strftime('%H:%M')}.
            
            REGLAS CRÍTICAS:
            - ELIMINA TODO sobre: Deportes, Farándula, Internacional, Sucesos Policiales, Horóscopos.
            - SOLO Economía, Gobierno, Aduana, Impuestos, Gestión Municipal.
            - PRIORIZA GEOGRÁFICAMENTE Cochabamba y Tarija.

            REGLA DE HORA (SIN EXCEPCIÓN):
            - Si 'HORA_DOC' tiene un valor (ej. 13:55, 11:08), ÚSALO. Es la hora real del artículo.
            - Si 'HORA_DOC' es "04:00", ignóralo (es un error de sistema) y estima una hora lógica de hoy.
            - No inventes horas si ya tienes el dato en 'HORA_DOC'.

            FORMATO:
            Agrupa por MEDIO (ID 1 al 12).
            *TITULAR EN MAYÚSCULAS Y NEGRITA*
            MEDIO EN MAYÚSCULAS Y NEGRITA
            HH:MM
            Resumen detallado (4-6 líneas).
            URL

            DATOS:
            {raw_data}
            """
            with st.spinner("Generando reporte..."):
                res = model.generate_content(prompt)
            
            if res.text:
                st.subheader("📋 Informe de Prensa:")
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
