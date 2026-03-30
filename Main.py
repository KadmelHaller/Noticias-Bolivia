import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# --- 1. CONFIGURACIÓN BÁSICA ---
st.set_page_config(page_title="Monitor Estratégico", layout="wide")
zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria).strftime('%d/%m/%Y')

# Palabras clave críticas para el filtro inicial
KEYWORDS = ["impuesto", "sin", "tribut", "factur", "fiscal", "recauda", "aduana", "gobierno", "arce", "ministro", "economia", "dolar", "banco", "subvención", "combustible"]

# --- 2. EL RASTREADOR (SCRAPING) ---
def buscar_noticias():
    fuentes = [
        {"n": "OPINIÓN", "u": "https://www.opinion.com.bo/", "r": "Cochabamba"},
        {"n": "LOS TIEMPOS", "u": "https://www.lostiempos.com/", "r": "Cochabamba"},
        {"n": "EL DEBER", "u": "https://eldeber.com.bo/", "r": "Santa Cruz"},
        {"n": "LA VOZ DIGITAL", "u": "https://lavoz.digital/", "r": "Santa Cruz"},
        {"n": "VISIÓN 360", "u": "https://www.vision360.bo/", "r": "Nacional"},
        {"n": "UNITEL", "u": "https://unitel.bo/", "r": "Nacional"}
    ]
    
    hallazgos = ""
    for f in fuentes:
        try:
            r = requests.get(f['u'], headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            # Buscamos en etiquetas de títulos y enlaces
            for el in soup.find_all(['h1', 'h2', 'h3', 'a']):
                texto = el.get_text().strip()
                link = el.get('href', '')
                if len(texto) > 35 and any(k in texto.lower() for k in KEYWORDS):
                    # Limpieza del link
                    full_link = link if link.startswith('http') else f['u'].rstrip('/') + link
                    hallazgos += f"MEDIO: {f['n']} | REGIÓN: {f['r']} | NOTICIA: {texto} | LINK: {full_link}\n"
        except: continue
    return hallazgos

# --- 3. EL ANALISTA (IA GEMINI 1.5 FLASH) ---
def procesar_con_ia(datos_crudos):
    try:
        # Usamos el nombre estándar que no debería dar error 404
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        FECHA DEL REPORTE: {fecha_hoy}
        Tu tarea es redactar un reporte de noticias sobre ECONOMÍA e IMPUESTOS de BOLIVIA.
        
        ESTRUCTURA OBLIGATORIA:
        1. COCHABAMBA
        (Aquí pones noticias de medios de Cbba o nacionales que afecten a Cbba)
        
        2. SANTA CRUZ
        (Aquí pones noticias de medios de SCZ o nacionales que afecten a SCZ)
        
        FORMATO POR NOTICIA (ESTRICTO):
        **TITULAR EN MAYÚSCULAS**
        **NOMBRE DEL MEDIO EN MAYÚSCULAS**
        Resumen técnico de 5 líneas (nombres, cargos y cifras exactas).
        Link directo en minúsculas.
        
        Separa cada noticia con un espacio simple. No uses negritas en el resumen.
        """
        
        respuesta = model.generate_content(prompt + "\n\nNOTICIAS PARA ANALIZAR:\n" + datos_crudos)
        return respuesta.text
    except Exception as e:
        return f"Error en la IA: {str(e)}"

# --- 4. INTERFAZ (LO QUE VERÁS EN PANTALLA) ---
st.title(f"🔍 Monitor de Prensa: {fecha_hoy}")
st.markdown("### Reporte Estratégico (Impuestos / Economía)")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    if st.button("🚀 INICIAR MONITOREO"):
        with st.spinner("Rastreando periódicos y analizando..."):
            # Paso 1: Scraping
            datos = buscar_noticias()
            
            if datos:
                # Paso 2: IA
                resultado = procesar_con_ia(datos)
                
                # Paso 3: Mostrar para copiar
                st.success("Monitoreo Finalizado")
                st.info("Copia el texto del cuadro de abajo y pégalo en tu Word:")
                
                # Cuadro de texto grande para copiar fácilmente
                st.text_area(label="Texto para copiar:", value=resultado, height=600)
            else:
                st.warning("No se encontraron noticias con las palabras clave hoy.")
else:
    st.warning("Por favor, ingresa tu API Key en la barra lateral para comenzar.")
