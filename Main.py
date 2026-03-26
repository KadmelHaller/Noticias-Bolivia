import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
from urllib.parse import urlparse, parse_qs

st.set_page_config(page_title="Monitoreo Bolivia Pro", page_icon="🇧🇴", layout="wide")

# --- CONFIGURACIÓN DE TIEMPO ---
zona_horaria = pytz.timezone('America/La_Paz')
ahora = datetime.now(zona_horaria)
fecha_hoy_bonita = ahora.strftime('%d/%m/%Y')

# --- FILTROS AMPLIADOS (Para asegurar que siempre salga algo) ---
TEMAS_OK = ["impuesto", "sin", "tribut", "factur", "fiscal", "econom", "gobiern", "arce", "dolar", "clausur", "aduana", "subsidio", "gasolina", "diesel", "presupuest", "banco", "comercio", "municip"]

def limpiar_url_google(url_google):
    """Extrae el link real de Facebook/TikTok/X de la redirección de Google"""
    if "google.com/url" in url_google:
        try:
            parsed = urlparse(url_google)
            res = parse_qs(parsed.query).get('q')
            if res: return res[0]
        except: pass
    return url_google

def es_relevante(texto, url):
    txt = (texto + url).lower()
    # Filtro de año: solo permitimos 2024, 2025, 2026 o noticias sin año (actuales)
    if any(old in txt for old in ["2021", "2022", "2023"]): return False
    return any(t in txt for t in TEMAS_OK)

st.title(f"📰 MONITOREO EN VIVO: {fecha_hoy_bonita}")
st.info("Nota: Se ha desactivado el historial. El reporte mostrará todo lo disponible en la red ahora mismo.")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def procesar_fuentes():
    fuentes = [
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/ultimas-noticias", "t": "Escrito", "r": "Cochabamba"},
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/seccion/cochabamba/", "t": "Escrito", "r": "Cochabamba"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/economia", "t": "Escrito", "r": "Santa Cruz"},
        {"n": "RRSS CBBA", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:x.com+impuestos+cochabamba+2026", "t": "Influencer", "r": "Cochabamba"},
        {"n": "RRSS SCZ", "u": "https://www.google.com/search?q=site:facebook.com+OR+site:x.com+impuestos+santa+cruz+2026", "t": "Influencer", "r": "Santa Cruz"},
        {"n": "UNITEL", "u": "https://unitel.bo/noticias/economia", "t": "TV", "r": "Nacional"},
        {"n": "URGENTE.BO", "u": "https://www.urgente.bo/economia", "t": "Digital", "r": "Nacional"}
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    data_final = ""
    pb = st.progress(0)
    
    for i, f in enumerate(fuentes):
        st.write(f"🔎 Revisando: {f['n']}...")
        pb.progress((i + 1) / len(fuentes))
        try:
            r = requests.get(f['u'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            vistos = 0
            
            for l in links:
                url_raw = l['href']
                url = limpiar_url_google(url_raw)
                
                # Validación de Redes Sociales
                if f['t'] == "Influencer":
                    if any(domain in url for domain in ["facebook.com", "x.com", "tiktok.com", "instagram.com"]):
                        # Solo aceptamos links que no sean de la propia plataforma de ayuda
                        if "sharer" in url or "google.com" in url: continue
                        titulo_rss = l.get_text().strip() if len(l.get_text()) > 10 else "Publicación relevante en Redes"
                        data_final += f"R: {f['r']} | T: {f['t']} | M: {f['n']} | TIT: {titulo_rss} | TXT: Post en Red Social | L: {url}\n\n"
                        vistos += 1
                
                # Validación de Medios Escritos/TV
                else:
                    if not url.startswith('http') or url.count('/') < 4: continue
                    titulo = l.get_text().strip()
                    if len(titulo) > 25 and es_relevante(titulo, url):
                        data_final += f"R: {f['r']} | T: {f['t']} | M: {f['n']} | TIT: {titulo} | TXT: Noticia detectada | L: {url}\n\n"
                        vistos += 1
                
                if vistos >= 6: break # Traemos más cantidad para asegurar reporte
        except Exception as e:
            st.warning(f"No se pudo conectar con {f['n']}")
            continue
            
    return data_final

if api_key:
    genai.configure(api_key=api_key)
    if st.button('🚀 GENERAR REPORTE SIN BLOQUEOS'):
        with st.status("Escaneando la red boliviana...") as status:
            raw_data = procesar_fuentes()
            if len(raw_data) > 100:
                status.update(label="IA analizando titulares encontrados...", state="running")
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"Eres un analista. Hoy es {fecha_hoy_bonita}. Organiza estas noticias: 1.Cochabamba, 2.Santa Cruz. Prioriza IMPUESTOS y SIN. Formato: TITULAR (MAYUS), MEDIO (MAYUS), resumen 4 líneas, URL. Si el link es de RRSS, indica que es una tendencia o denuncia digital."
                    res = model.generate_content([prompt, raw_data])
                    status.update(label="¡Reporte generado!", state="complete")
                    processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', res.text)
                    st.markdown(f'<div style="font-family:serif; font-size:13.3px; text-align:justify; background:white; color:black; padding:25px; border:1px solid #ccc;">{processed.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error en IA: {e}")
            else:
                st.warning("No se encontraron noticias ni publicaciones en RRSS con los filtros actuales. Intenta en 15 minutos.")
