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

st.title(f"📰 MONITOREO PROFUNDO: {fecha_ref}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def calcular_hora_relativa(texto):
    """Convierte 'hace x minutos' en una hora HH:MM real."""
    texto = texto.lower()
    try:
        if 'minuto' in texto:
            mins = int(re.search(r'(\d+)', texto).group(1))
            hora_real = ahora - timedelta(minutes=mins)
            return hora_real.strftime('%H:%M')
        if 'hora' in texto:
            hrs = int(re.search(r'(\d+)', texto).group(1))
            hora_real = ahora - timedelta(hours=hrs)
            return hora_real.strftime('%H:%M')
    except:
        pass
    return None

def extraer_datos_articulo(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        hora_interna = ""
        metadatos_raw = ""

        # 1. BUSCAR TIEMPO RELATIVO (Caso Unitel: 'hace 1 minuto')
        etiquetas_tiempo = soup.find_all(['span', 'div', 'p', 'time'], class_=re.compile(r'time|date|fecha|relativo', re.I))
        for tag in etiquetas_tiempo:
            txt_t = tag.get_text().strip()
            res_relativo = calcular_hora_relativa(txt_t)
            if res_relativo:
                hora_interna = res_relativo
                break

        # 2. JSON-LD (Si no hubo relativo)
        if not hora_interna:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        target = item.get('@graph', [item])
                        for node in target:
                            if 'datePublished' in node:
                                # Extraer solo la hora y ajustar si es necesario
                                dt_str = node['datePublished']
                                dt_match = re.search(r'(\d{2}):(\d{2})', dt_str)
                                if dt_match:
                                    # Si detectamos que es UTC (termina en Z o +00), restamos 4 horas para Bolivia
                                    hh, mm = int(dt_match.group(1)), dt_match.group(2)
                                    if 'Z' in dt_str or '+00' in dt_str:
                                        hh = (hh - 4) % 24
                                    hora_interna = f"{hh:02d}:{mm}"
                                    break
                except: continue
                if hora_interna: break

        # 3. CONTENIDO
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
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    data_raw = ""
    pb = st.progress(0)
    
    for i, fuente in enumerate(fuentes):
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
                        data_raw += f"ORDEN: {i+1} | MEDIO: {fuente['nombre']} | HORA_INT: {h_int} | LINK: {full_link} | TXT: {txt[:600]}\n"
        except: continue
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR MONITOREO CORREGIDO'):
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
            ORDEN: Según 'ORDEN' (1 al 12).

            REGLA DE HORA (JERARQUÍA):
            1. 'HORA_INT' (Si tiene HH:MM, es la prioridad absoluta).
            2. Si 'HORA_INT' está vacío, busca en el 'LINK' (patrón de 4 números tras la fecha).
            3. Si nada funciona, estima y pon "(aprox.)". No uses 04:00 a menos que sea real.

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
