import streamlit as st
import google.generativeai as genai
from datetime import datetime

st.set_page_config(page_title="IA News Bolivia", page_icon="🇧🇴")
st.title("🤖 RESUMEN INTELIGENTE: BOLIVIA")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # BUSQUEDA AUTOMÁTICA DE MODELO DISPONIBLE
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Seleccionamos el primero que sea flash o pro
        model_name = next((m for m in available_models if "flash" in m), available_models[0])
        
        model = genai.GenerativeModel(model_name)

        if st.button('🚀 GENERAR RESUMEN AHORA'):
            with st.spinner(f'Usando modelo {model_name}...'):
                fecha_hoy = datetime.now().strftime('%d/%m/%Y')
                
                prompt = f"""
                Hoy es {fecha_hoy}. Busca noticias reales de hoy en Bolivia.
                Medios: Opinión Cochabamba, Los Tiempos, La Voz de Tarija y TV (Unitel, Red Uno).
                Temas: Economía, Impuestos y Política.
                
                Entrega 6 noticias con este formato:
                **TITULAR: [MAYÚSCULAS Y NEGRITA]**
                **MEDIO: [MAYÚSCULAS Y NEGRITA]**
                Resumen: [3 a 4 líneas]
                Enlace: https://directausa.com/
                """
                
                response = model.generate_content(prompt)
                st.success("¡Resumen generado!")
                st.markdown(response.text)

    except Exception as e:
        st.error("Error de conexión con Google AI")
        st.info(f"Detalle: {e}")
else:
    st.warning("👈 Ingresa tu API Key.")
