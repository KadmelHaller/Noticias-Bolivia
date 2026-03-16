import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import json

# Configuración de página
st.set_page_config(page_title="Monitoreo Bolivia Pro", page_icon="🇧🇴", layout="wide")

# --- LÓGICA DE TIEMPO BOLIVIA ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')

st.title(f"📰 MONITOREO TÉCNICO: {fecha_hoy_bonita}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def extraer_hora_especifica(soup, medio):
    """Busca la hora en JSON-LD, etiquetas de tiempo o metadatos."""
    # 1. Intentar con JSON-LD (Más preciso para noticias modernas)
    for s in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(s.string)
            graph = data.get('@graph', [data]) if isinstance(data, dict) else data
            for node in (graph if isinstance(graph, list) else [graph]):
                date_str = node.get('datePublished') or node.get('dateModified')
                if date_str:
                    m = re.search(r'(\d{2}):(\d{2})', date_str)
                    if m: 
                        hh, mm = int(m.group(1)), m.group(2)
                        if medio == "ATB": hh = (hh - 4) % 24 # Ajuste huso horario ATB
                        return f"{hh:02d}:{mm}"
        except: continue

    # 2. Buscar en etiquetas HTML comunes
    for tag in ['time', 'span', 'div']:
        el = soup.find(tag, class_=re.compile(r'date|time|hora|published', re.I))
        if el:
            m = re.search(r'(\d{1,2}:\d{2})', el.get_text())
            if m: return m.group(1)

    # 3. Metadatos OpenGraph (Último recurso)
    meta_time = soup.find("meta", property="article:published_time")
    if meta_time:
        m = re.search(r'T(\d{2}):(\d{2})', meta_time['content'])
        if m: return f"{m.group(1)}:{m.group(2)}"

    return ""

def procesar_monitoreo():
    fuentes = [
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/"},
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/"},
        {"nombre": "LA RAZÓN", "url": "https://larazon.bo/categoria/nacional/"},
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
        st.write(f"📡 {fuente['nombre']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=12)
            if r.status_code != 200: continue
                
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            procesados, vistos = 0, set()
            
            for l in links:
                url_n = l['href']
                if not url_n.startswith('http'):
                    url_n = "https://larazon.bo" + url_n if "larazon" in fuente['url'] else fuente['url'].rstrip('/') + "/" + url_n.lstrip('/')
                
                texto_enlace = l.get_text().strip()
                if len(texto_enlace) < 25 or url_n in vistos or any(x in url_n for x in ['/tag/', '/autor/']): continue
                
                try:
                    rn = requests.get(url_n, headers=headers, timeout=8)
                    if rn.status_code != 200: continue
                    
                    soup_n = BeautifulSoup(rn.text, 'html.parser')
                    h = extraer_hora_especifica(soup_n, fuente['nombre'])
                    p_tags = soup_n.find_all('p', limit=8)
                    cuerpo = " ".join([p.get_text().strip() for p in p_tags if len(p.get_text()) > 30])
                    
                    if len(cuerpo) > 180:
                        data_final += f"MEDIO: {fuente['nombre']} | HORA: {h} | TITULAR: {texto_enlace} | TXT: {cuerpo[:1000]} | LINK: {url_n}\n\n"
                        vistos.add(url_n)
                        procesados += 1
                except: continue
                if procesados >= 5: break
        except: continue
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE FINAL'):
        raw_data = procesar_monitoreo()
        if len(raw_data) > 300:
            try:
                model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
                prompt = f"""
                HOY ES: {fecha_hoy_bonita}.
                OBJETIVO: Generar un reporte informativo técnico y limpio.
                FILTRO TEMÁTICO: Solo noticias de IMPUESTOS, ECONOMÍA y GOBIERNO BOLIVIANO.
                
                JERARQUÍA DE ORDENAMIENTO (OBLIGATORIO):
                1. ORDEN POR MEDIO: Primero OPINIÓN, segundo LOS TIEMPOS, tercero LA VOZ DE TARIJA, cuarto LA RAZÓN, quinto Canales de TV (Unitel, Red Uno, ATB, etc.), sexto Medios Digitales.
                2. ORDEN POR GEOGRAFÍA (dentro de cada grupo o en general): Priorizar noticias de COCHABAMBA primero, TARIJA segundo, y Nacional tercero.
                
                Si un canal nacional habla de Cochabamba, debe subir en prioridad dentro de su categoría.
                
                ESTRUCTURA DE CADA NOTICIA:
                **TITULAR EN MAYÚSCULAS**
                **NOMBRE DEL MEDIO**
                **Hrs. HH:MM** (Si no hay hora en los datos, pon "Sin hora registrada")
                Resumen detallado y profesional (4 a 6 líneas).
                URL (Enlace directo sin etiquetas adicionales)
                
                Formato final: Texto justificado, separar noticias con doble espacio.
                """
                res = model.generate_content([prompt, raw_data])
                st.subheader("📋 Resumen Informativo:")
                # Formateo estético
                processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                st.markdown(f'''
                    <div style="font-family:'Times New Roman', serif; font-size:14px; text-align:justify; background:white; color:black; padding:30px; border:1px solid #ddd; line-height:1.6;">
                        {processed.replace("\n", "<br>")}
                    </div>
                ''', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error en IA: {str(e)}")
        else:
            st.warning("No se recolectaron suficientes datos técnicos para generar el reporte.")
