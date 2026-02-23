import streamlit as st
import google.generativeai as genai
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(page_title="IA News Bolivia", page_icon="🇧🇴")

st.title("🤖 RESUMEN INTELIGENTE: BOLIVIA")
st.markdown("Fuentes: Opinión, Los Tiempos, La Voz de Tarija y TV.")

# 2. Barra lateral para la API Key
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

# 3. Lógica principal
if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        if st.button('🚀 GENERAR RESUMEN AHORA'):
            with st.spinner('Gemini está analizando las noticias...'):
                fecha_hoy = datetime.now().strftime('%d/%m/%Y')
                
                prompt = f"""
                Hoy es {fecha_hoy}. Busca noticias actuales de Bolivia (Cochabamba y Tarija).
                Fuentes: Diarios Opinión, Los Tiempos, La Voz de Tarija y redes de TV (Unitel, Red Uno).
                Temas: Economía, Impuestos y Política.
                
                Entrega las 6 noticias más importantes con este formato exacto:
                
                **TITULAR: [TITULAR EN MAYÚSCULAS Y NEGRITA]**
                **MEDIO: [MEDIO EN MAYÚSCULAS Y NEGRITA]**
                Resumen: [3 a 4 líneas de análisis]
                Enlace: https://directausa.com/
                
                No incluyas introducciones ni despedidas.
                """
                
                response = model.generate_content(prompt)
                
                if response.text:
                    st.success("Resumen generado")
                    st.markdown(response.text)
                else:
                    st.error("La IA no devolvió resultados.")

    except Exception as e:
        st.error(f"Error técnico: {e}")
else:
    st.warning("👈 Ingresa tu API Key en la barra lateral.")

st.sidebar.markdown("---")
st.sidebar.write("Formato compatible con Word")
 
