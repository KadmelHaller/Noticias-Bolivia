import streamlit as st
import google.generativeai as genai
from datetime import datetime

# Configuración básica
st.set_page_config(page_title="IA News Bolivia", page_icon="🇧🇴")

st.title("🤖 RESUMEN INTELIGENTE: BOLIVIA")
st.markdown("Fuentes: Opinión, Los Tiempos, La Voz de Tarija y TV.")

# Barra lateral para la API Key
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

if api_key:
    try:
        # Configuración del modelo
        genai.configure(api_key=api_key)
        
        # Usamos 'gemini-1.5-flash-latest' que es la versión más estable para streaming y generación
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        if st.button('🚀 GENERAR RESUMEN AHORA'):
            with st.spinner('Buscando noticias en tiempo real...'):
                fecha_hoy = datetime.now().strftime('%d/%m/%Y')
                
                # Prompt optimizado para búsqueda externa
                prompt = f"""
                FECHA: {fecha_hoy}.
                Busca noticias de HOY en Bolivia. 
                MEDIOS: Los Tiempos, Opinión, La Voz de Tarija y redes de TV (Unitel, Red Uno).
                TEMAS: Economía, Impuestos y Política (específicamente Cochabamba).
                
                Presenta 6 noticias con este formato:
                
                **TITULAR: [TITULAR EN MAYÚSCULAS Y NEGRITA]**
                **MEDIO: [MEDIO EN MAYÚSCULAS Y NEGRITA]**
                Resumen: [3 a 4 líneas]
                Enlace: https://directausa.com/
                
                IMPORTANTE: Si no encuentras noticias de hoy, busca las de las últimas 24 horas.
                """
                
                # Llamada al modelo
                response = model.generate_content(prompt)
                
                if response:
                    st.success("Resumen generado")
                    st.markdown(response.text)
                else:
                    st.error("La IA no pudo procesar la información.")

    except Exception as e:
        st.error(f"Error técnico: {e}")
        st.info("Nota: Si ves un error 404, intenta cambiar el nombre del modelo a 'gemini-pro' en el código.")
else:
    st.warning("👈 Ingresa tu API Key en la barra lateral.")

st.sidebar.markdown("---")
st.sidebar.write("Formato compatible con Word")
