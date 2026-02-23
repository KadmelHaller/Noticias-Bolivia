import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pytz

# 1. Configuración de la página
st.set_page_config(page_title="IA News Bolivia Pro", page_icon="🇧🇴")

# 2. Fecha automática
zona_horaria = pytz.timezone('America/La_Paz')
fecha_actual = datetime.now(zona_horaria)
fecha_texto = fecha_actual.strftime('%d/%m/%Y')

st.title("📰 REPORTE DIARIO DE NOTICIAS")
st.caption(f"Fecha de consulta: {fecha_texto}")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # Usamos la herramienta de búsqueda de Google (Google Search Retrieval)
        # Esto es lo que permite que la IA "navegue" de verdad
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            tools=[{"google_search_retrieval": {}}] 
        )

        if st.button('🚀 GENERAR RESUMEN REAL AHORA'):
            with st.spinner('Navegando en Los Tiempos, Opinión y La Voz de Tarija...'):
                
                # Prompt agresivo: Prohibimos excusas y obligamos a buscar
                prompt = f"""
                FECHA ACTUAL: {fecha_texto}.
                TAREA: Usa la herramienta de búsqueda de Google para encontrar noticias REALES publicadas HOY {fecha_texto} en Bolivia.
                
                FUENTES ESPECÍFICAS: 
                - Portales web de Los Tiempos y Opinión (Cochabamba).
                - Portal web de La Voz de Tarija.
                - Web de Unitel y Red Uno.
                
                TEMAS: Economía, Impuestos y Política.
                
                REGLAS CRÍTICAS:
                1. NO des explicaciones sobre tus límites de fecha o entrenamiento.
                2. NO inventes noticias ni generes simulaciones.
                3. Si la búsqueda no arroja resultados de hoy, busca noticias de las últimas 24 horas.
                4. Entrega exactamente 6 noticias con este formato:

                **TITULAR: [TITULAR REAL EN MAYÚSCULAS Y NEGRITA]**
                **MEDIO: [NOMBRE DEL MEDIO EN MAYÚSCULAS Y NEGRITA]**
                Resumen: [3 a 4 líneas de análisis real]
                Enlace: https://www.realtrue.org/espanol/

                Si entiendes, comienza directamente con las noticias.
                """
                
                response = model.generate_content(prompt)
                
                if response.text:
                    st.success(f"Noticias encontradas para hoy {fecha_texto}")
                    st.markdown(response.text)
                else:
                    st.warning("La búsqueda no devolvió resultados específicos. Intenta presionar el botón nuevamente.")

    except Exception as e:
        st.error("Error en la búsqueda en vivo.")
        st.info(f"Detalle: {e}")
else:
    st.warning("👈 Ingresa tu API Key para activar la búsqueda web.")
