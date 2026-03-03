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
    """Extrae texto, hora de metadatos JSON-LD y etiquetas internas."""
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        hora_interna = ""
        metadatos_raw = ""

        # 1. BUSCAR EN JSON-LD (La hora más precisa: datePublished)
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    target = item.get('@graph', [item])
                    for node in target:
                        if 'datePublished' in node:
                            dt_match = re.search(r'(\d{2}:\d{2})', node['datePublished'])
                            if dt_match:
                                hora_interna = dt_match.group(1)
                                break
            except: continue
            if hora_interna: break

        # 2. CAPTURAR OTROS METADATOS (Para la jerarquía de la IA)
        meta_pub = soup.find("meta", property="article:published_time") or \
                   soup.find("meta", itemprop="datePublished")
        if meta_pub:
            metadatos_raw = meta_pub.get("content", "")

        # 3. EXTRAER TEXTO PARA FILTRADO Y RESUMEN
        parrafos = soup.find_all('p', limit=6)
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
    st_info = st.empty()
    
    for i, fuente in enumerate(fuentes):
        st_info.text(f"Procesando {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            articulos = soup.find_all(['h1', 'h2', 'h3'], limit=10)
            
            for art in articulos:
                a_tag = art.find('a') or art.find_parent('a')
                if a_tag and a_tag.get('href'):
                    link_href = a_tag['href']
                    full_link = link_href if link_href.startswith('http') else fuente['base'].rstrip('/') + link_href
                    
                    # SCRAPING PROFUNDO
                    h_interna, m_raw, texto_it = extraer_datos_articulo(full_link, headers)
                    
                    if len(texto_it) > 100:
                        # Enviamos todos los datos recolectados para que la IA aplique la jerarquía
                        data_raw += f"ORDEN_FUENTE: {i+1} | MEDIO: {fuente['nombre']} | HORA_INTERNA: {h_interna} | METADATO_PAGINA: {m_raw} | TEMA: {art.get_text().strip()} | LINK: {full_link} | TEXTO: {texto_it[:900]}\n"
        except: continue
    
    pb.empty()
    st_info.empty()
    return data_raw

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR MONITOREO PROFUNDO'):
        noticias_raw = extraer_noticias()
        if len(noticias_raw) > 500:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            HOY ES: {fecha_ref}. HORA ACTUAL EN BOLIVIA: {ahora.strftime('%H:%M')}.
            
            TAREA: Resumen técnico para monitoreo de prensa.
            
            FILTRADO ESTRICTO:
            - ELIMINA noticias de Deportes, Farándula, Espectáculos, Horóscopo o Internacional.
            - PRIORIZA: Economía, Impuestos, Gobierno.
            - PRIORIZA GEOGRÁFICAMENTE: Cochabamba y Tarija.
            - ORDENA LOS RESULTADOS DE ACUERDO AL NÚMERO DE 'ORDEN_FUENTE'.
            
            REGLA DE HORA (JERARQUÍA ESTRICTA):
            1. Usa la hora encontrada en 'HORA_INTERNA'. Límpiala para que sea solo HH:MM.
            2. Si 'HORA_INTERNA' no tiene la hora, búscala en el texto del 'LINK' (ej. números como 1108).
            3. Si 'HORA_INTERNA' no tiene la hora y 'LINK' no tiene la hora, búscala en 'METADATO_PAGINA'.
            4. Solo como último recurso estima una hora lógica y pon "(aprox.)".

            ORDEN DE SALIDA (ESTRICTO):
            *TITULAR EN MAYÚSCULAS Y NEGRITA*
            MEDIO EN MAYÚSCULAS Y NEGRITA
            HH:MM (Sin etiquetas como 'Hora:')
            Párrafo informativo (4 a 6 líneas detalladas).
            URL

            ENTRADA:
            {noticias_raw}
            """
            
            with st.spinner("IA aplicando filtros y jerarquía de horas..."):
                res = model.generate_content(prompt)
                
            if res.text:
                st.subheader("📋 Formato Final (Times New Roman 10):")
                # Limpiar posibles negritas markdown sobrantes y aplicar formato HTML
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                
                html_final = f"""
                <div style="font-family: 'Times New Roman', serif; font-size: 13.3px; color: black; background-color: white; padding: 25px; border: 1px solid #ccc; line-height: 1.3; text-align: justify;">
                    {processed.replace("\n", "<br>")}
                </div>
                """
                st.markdown(html_final, unsafe_allow_html=True)
                st.success("Monitoreo generado siguiendo el orden de fuentes y jerarquía de horas.")
