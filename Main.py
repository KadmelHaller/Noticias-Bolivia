import streamlit as st
import google.generativeai as genai
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="IA News Bolivia", page_icon="🇧🇴")

st.title("🤖 RESUMEN INTELIGENTE: BOLIVIA")
st.markdown("Fuentes: Opinión, Los Tiempos, La Voz de Tarija y TV.")

# Barra lateral para la API Key
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

if api_key:
    try:
        # Forzamos la configuración inicial
        genai.configure(api_key=api_key)
        
        # Intentamos usar el modelo flash más estable
        # Esta configuración suele evitar el error de la versión v1beta
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 2048,
            }
        )

        if st.button('🚀 GENERAR RESUMEN AHORA'):
            with st.spinner('Buscando noticias en tiempo real...'):
                fecha_hoy = datetime.now().strftime('%d/%m/%Y')
                
                # El prompt incluye instrucciones de búsqueda
                prompt = f"""
                Hoy es {fecha_hoy}. Busca y resume las noticias más importantes de Bolivia.
                ENFOQUE: Cochabamba y Tarija.
                FUENTES: Los Tiempos, Opinión, La Voz de Tarija y redes de TV (Unitel, Red Uno).
                TEMAS: Economía, Impuestos y Política.
                
                Presenta 6 noticias siguiendo este formato EXACTO:
                
                **TITULAR: [TITULAR EN MAYÚSCULAS Y NEGRITA]**
                **MEDIO: [MEDIO EN MAYÚSCULAS Y NEGRITA]**
                Resumen: [3 a 4 líneas de análisis]
                Enlace: https://directa.cat/
                
                No incluyas introducciones ni despedidas.
                """
                
                # Generación de contenido
                response = model.generate_content(prompt)
                
                if response:
                    st.success("Resumen generado")
                    st.markdown(response.text)
                else:
                    st.error("No se recibió respuesta de la IA.")

    except Exception as e:
        # Mostramos un mensaje más amigable y el error detallado abajo
        st.error("Hubo un problema con la conexión de la API.")
        st.info(f"Detalle técnico: {e}")
else:
    st.warning("👈 Ingresa tu API Key en la barra lateral.")

st.sidebar.markdown("---")
st.sidebar.write("Formato listo para Word")
