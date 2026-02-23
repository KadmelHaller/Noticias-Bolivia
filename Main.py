import streamlit as st
import google.generativeai as genai
from datetime import datetime

st.set_page_config(page_title="IA News Bolivia", page_icon="🇧🇴")
st.title("📰 RESUMEN DE NOTICIAS EN TIEMPO REAL")

api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # Auto-detección del modelo disponible
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = next((m for m in available_models if "flash" in m), available_models[0])
        model = genai.GenerativeModel(model_name)

        if st.button('🚀 BUSCAR NOTICIAS DE HOY'):
            with st.spinner('Accediendo a portales de noticias bolivianos...'):
                # Usamos una instrucción que fuerce la búsqueda externa
                prompt = """
                Realiza una búsqueda en internet en tiempo real. 
                Necesito las noticias reales de HOY, verificando la fecha real.
                
                Busca específicamente en:
                1. Los Tiempos (lostiempos.com)
                2. Opinión (opinion.com.bo)
                3. La Voz de Tarija (lavozdetarija.com)
                4. Redes sociales de canales de televisión en Bolivia.

                Filtra noticias de: ECONOMÍA, IMPUESTOS y POLÍTICA en Cochabamba, Bolivia.
                
                Presenta entre 5 y 7 noticias con este formato:
                
                **[TITULAR EXACTO Y REAL EN MAYÚSCULAS Y NEGRITA]**
                Espacio
                **[NOMBRE DEL MEDIO EN MAYÚSCULAS Y NEGRITA]**
                Espacio
                Resumen: [Escribe 3 a 4 líneas de lo que está pasando realmente hoy]
                Enlace: [Detalla el enlace completo y real de la noticia, no solo el dominio] 
                
                No digas que no puedes acceder al futuro pero tampoco uses noticias de otras fechas, solamente de hoy. Usa tu función de búsqueda web integrada para ver los portales de hoy.
                """
                
                response = model.generate_content(prompt)
                st.success("Información actualizada")
                st.markdown(response.text)

    except Exception as e:
        st.error("Error al obtener noticias")
        st.info(f"Detalle: {e}")
else:
    st.warning("👈 Ingresa tu API Key en la barra lateral.")
