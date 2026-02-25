import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

st.set_page_config(page_title="Monitoreo SIN CBBA", page_icon="🇧🇴")
zona_horaria = pytz.timezone('America/La_Paz')
# Obtenemos la fecha dinámicamente para que el prompt siempre esté actualizado
ahora = datetime.now(zona_horaria)
fecha_hoy_str = ahora.strftime('%A %d de %B de %Y') 

st.title(f"📰 MONITOREO DE NOTICIAS - SIN CBBA: {ahora.strftime('%d/%m/%Y')}")
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

def detectar_modelo(key):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(url)
        if res.status_code == 200:
            modelos = res.json().get('models', [])
            for m in modelos:
                if "flash" in m['name'] and "generateContent" in m['supportedGenerationMethods']:
                    return m['name']
        return "models/gemini-1.5-flash"
    except: return "models/gemini-1.5-flash"

def extraer_noticias():
    fuentes = [
        {"nombre": "OPINIÓN", "url": "https://www.opinion.com.bo/", "base": "https://www.opinion.com.bo"},
        {"nombre": "LOS TIEMPOS", "url": "https://www.lostiempos.com/", "base": "https://www.lostiempos.com"},
        {"nombre": "LA VOZ DE TARIJA", "url": "https://lavozdetarija.com/", "base": "https://lavozdetarija.com"},
        {"nombre": "UNITEL", "url": "https://unitel.bo/economia/", "base": "https://unitel.bo"},
        {"nombre": "RED UNO", "url": "https://www.reduno.com.bo/", "base": "https://www.reduno.com.bo"},
        {"nombre": "ATB", "url": "https://www.atb.com.bo/", "base": "https://www.atb.com.bo"},
        {"nombre": "BOLIVIA TV", "url": "https://www.boliviatv.bo/principal/", "base": "https://www.boliviatv.bo"},
        {"nombre": "URGENTE BO", "url": "https://www.urgente.bo/", "base": "https://www.urgente.bo"},
        {"nombre": "BOLIVISION", "url": "https://www.redbolivision.tv.bo/", "base": "https://www.redbolivision.tv.bo"},
        {"nombre": "CADENA A", "url": "https://www.cadenaa.tv/", "base": "https://www.cadenaa.tv"},
        {"nombre": "IN NOTICIAS", "url": "https://innoticiasbo.com/", "base": "https://innoticiasbo.com"},
        {"nombre": "ENFOQUE NEWS", "url": "https://enfoquenews.com.bo/", "base": "https://enfoquenews.com.bo"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    data_acumulada = ""

    for fuente in fuentes:
        try:
            r = requests.get(fuente['url'], headers=headers, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            for tag in soup.find_all(['h1', 'h2', 'h3'], limit=15):
                titulo = tag.get_text().strip()
                a_tag = tag.find('a') or tag.find_parent('a')
                if a_tag and a_tag.get('href') and len(titulo) > 25:
                    link = a_tag['href']
                    full_link = link if link.startswith('http') else fuente['base'].rstrip('/') + link
                    data_acumulada += f"Fuente: {fuente['nombre']} | Noticia: {titulo} | URL: {full_link}\n"
        except: continue
    return data_acumulada

if api_key:
    if st.button('🚀 GENERAR MONITOREO DEL DÍA'):
        with st.spinner('Analizando vigencia y ordenando noticias...'):
            modelo = detectar_modelo(api_key)
            noticias_raw = extraer_noticias()
            
            if len(noticias_raw) > 300:
                # Prompt reforzado con reglas de exclusión
                prompt = f"""
                Hoy es {fecha_hoy_str}. 
                Eres un analista de medios experto en Bolivia. 
                
                DATOS EXTRAÍDOS:
                {noticias_raw}
                
                REGLAS DE FILTRADO (MUY IMPORTANTES):
                1. SOLO noticias publicadas HOY {fecha_hoy_str}. 
                2. ELIMINA cualquier noticia que mencione fechas pasadas, eventos de hace días o que el contexto indique que no es de hoy.
                3. PRIORIZA: Economía, Impuestos y Gobierno.
                4. UBICACIÓN: Máxima prioridad a COCHABAMBA y TARIJA.

                ORDEN DE PRIORIDAD DE MEDIOS (Presenta en este orden exacto):
                1. OPINIÓN
                2. LOS TIEMPOS
                3. LA VOZ DE TARIJA
                4. TELEVISIÓN (BOLIVIA TV, UNITEL, RED UNO, ATB, BOLIVISIÓN, CADENA A)
                5. DIGITALES (URGENTE BO, IN NOTICIAS, ENFOQUE NEWS)

                FORMATO DE SALIDA (ESTRICTO):
                **TITULAR EN MAYÚSCULAS Y NEGRITA**
                
                **MEDIO EN MAYÚSCULAS Y NEGRITA**
                
                resumen de 4 a 6 líneas en minúsculas, explicando el suceso actual de forma profesional.
                
                url completa en minúsculas.

                INSTRUCCIONES FINALES:
                - Usa dos saltos de línea entre cada bloque.
                - NO pongas etiquetas como "Resumen:" o "URL:".
                - No inventes noticias. Si no hay noticias de hoy en un medio, pasa al siguiente.
                - Detalla nombres y cargos de las personas de cada nota, verificando la veracidad de estos datos.
                """
                
                url_api = f"https://generativelanguage.googleapis.com/v1beta/{modelo}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "safetySettings": [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                    ],
                    "generationConfig": {
                        "temperature": 0.0, # Mínima creatividad para máxima precisión histórica
                        "topP": 1,
                        "maxOutputTokens": 2048
                    }
                }
                
                res = requests.post(url_api, json=payload)
                if res.status_code == 200:
                    respuesta_texto = res.json()['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(respuesta_texto)
                else:
                    st.error("Error al procesar con la IA.")
            else:
                st.error("No se pudo obtener información suficiente de los portales.")
