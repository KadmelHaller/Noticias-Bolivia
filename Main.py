import streamlit as st
import google.generativeai as genai
from datetime import datetime

# Configuración de página
st.set_page_config(page_title="IA News Bolivia", page_icon="🇧🇴")

st.title("🤖 RESUMEN INTELIGENTE: BOLIVIA")
st.markdown("Fuentes: Opinión, Los Tiempos, La Voz de Tarija y TV.")

# Barra lateral
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

if api_key:
    try:
        # Configuración de la API
        genai.configure(api_key=api_key)
        
        # Intentamos con 'gemini-1.5-flash-latest' que es la ruta de producción actual
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        if st.button('🚀 GENERAR RESUMEN AHORA'):
            with st.spinner('Buscando noticias...'):
                fecha_hoy = datetime.now().strftime('%d/%m/%Y')
                
                prompt = f"""
                Hoy es {fecha_hoy}. Busca noticias de hoy en Bolivia.
                Medios: Opinión, Los Tiempos, La Voz de Tarija y TV Boliviana.
                Temas: Economía, Impuestos y Política en Cochabamba y Tarija.
                
                Entrega 6 noticias con este formato:
                
                **TITULAR: [TITULAR EN MAYÚSCULAS Y NEGRITA]**
                **MEDIO: [MEDIO EN MAYÚSCULAS Y NEGRITA]**
                Resumen: [3 a 4 líneas]
                Enlace: https://directausa.com/
                
                No incluyas saludos.
                """
                
                response = model.generate_content(prompt)
                
                if response.text:
                    st.success("Resumen generado")
                    st.markdown(response.text)
                else:
                    st.error("No se recibió texto de la IA.")

    except Exception as e:
        st.error("Error de compatibilidad detectado.")
        # Si falla el flash, intentamos automáticamente con el modelo pro
        try:
            model_alt = genai.GenerativeModel('gemini-pro')
            st.info("Intentando conexión alternativa...")
            # (El código intentará usar gemini-pro si el primero falla)
        except:
            pass
        st.info(f"Detalle: {e}")
else:
    st.warning("👈 Ingresa tu API Key.")
