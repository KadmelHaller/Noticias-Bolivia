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
fecha_hoy_str = ahora.strftime('%Y/%m/%d') # Formato común en URLs
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO DE PRENSA: {fecha_hoy_bonita}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_datos_articulo(url, headers, nombre_medio):
    try:
        r = requests.get(url, headers=headers, timeout=12)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 1. FILTRO DE FECHA ESTRICTO (Solo hoy)
        # Si la URL contiene una fecha y no es la de hoy, descartar
        fecha_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if fecha_match:
            fecha_url = f"{fecha_match.group(1)}/{fecha_match.group(2)}/{fecha_match.group(3)}"
            if fecha_url != fecha_hoy_str:
                return None, None

        # 2. EXTRACCIÓN DE HORA
        texto_completo = soup.get_text(" ", strip=True)
        hora_detectada = ""

        if nombre_medio == "OPINIÓN":
            # Ignoramos el reloj de cabecera buscando después del primer párrafo
            cuerpo = soup.find('article') or soup.find('div', class_='cuerpo')
            if cuerpo:
                m = re.search(r'(\d{1,2}:\d{2})', cuerpo.get_text())
                if m: hora_detectada = m.group(1)
        
        elif nombre_medio == "LOS TIEMPOS":
            m = re.search(r'(\d{1,2})h(\d{2})', texto_completo)
            if m: hora_detectada = f"{m.group(1)}:{m.group(2)}"

        if not hora_detectada:
            # Buscamos patrones de hora estándar evitando el 04:00 de sistema
            matches = re.findall(r'(\d{1,2}:\d{2})', texto_completo)
            for m in matches:
                if m != "04:00" and m != ahora.strftime('%H:%M'):
                    hora_detectada = m
                    break

        # 3. CONTENIDO
        parrafos = soup.find_all('p', limit=6)
        contenido = " ".join([p.get_text().strip() for p in parrafos])
        if len(contenido) < 120: return None, None
        
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
    
    for i, fuente in enumerate(fuentes):
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Para Tarija buscamos específicamente en su estructura de artículos
            links = soup.find_all(['a', 'article'], href=True) if fuente['nombre'] != "LA VOZ DE TARIJA" else soup.select('article a[href]')
            if not links: links = soup.find_all('a', href=True)

            procesados = 0
            vistos = set()
            for l in links:
                if procesados >= 8: break
                url_n = l['href'] if l.name == 'a' else l.find('a')['href']
                full_link = url_n if url_n.startswith('http') else fuente['base'].rstrip('/') + url_n
                
                if full_link in vistos or any(x in full_link for x in ['/tag/', '/category/', '/author/']): continue
                
                h, t = extraer_datos_articulo(full_link, headers, fuente['nombre'])
                if t:
                    data_raw += f"ID:{i+1} | MEDIO:{fuente['nombre']} | H:{h} | TEMA:{l.get_text().strip()[:100]} | L:{full_link} | TXT:{t[:800]}\n"
                    vistos.add(full_link)
                    procesados += 1
        except: continue
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE DEL DÍA'):
        raw_data = extraer_noticias()
        if len(raw_data) > 200:
            modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model = genai.GenerativeModel(next((m for m in modelos if "1.5-flash" in m), modelos[0]))
            
            prompt = f"""
            HOY ES: {fecha_hoy_bonita}.
            
            TAREA:
            - Selecciona noticias SOLO de Economía, Impuestos, Aduana, Gobierno y Gestión Municipal.
            - ELIMINA Deportes, Farándula, Sucesos Policiales e Internacional.
            - PRIORIZA Cochabamba y Tarija.

            REGLAS DE FORMATO:
            - NO agrupes por medio. Genera una lista continua.
            - Usa la hora de 'H'. Si está vacía o es la actual ({ahora.strftime('%H:%M')}), estima una hora de HOY con "(aprox.)".
            - ELIMINA cualquier noticia que no sea de HOY ({fecha_hoy_bonita}).

            SALIDA:
            *TITULAR EN MAYÚSCULAS Y NEGRITA*
            MEDIO EN MAYÚSCULAS Y NEGRITA
            HH:MM
            Resumen informativo (4-6 líneas).
            URL
            (espacio entre noticias)

            DATOS:
            {raw_data}
            """
            res = model.generate_content(prompt)
            if res.text:
                st.subheader("📋 Resumen de Prensa:")
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
