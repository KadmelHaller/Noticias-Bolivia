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
        # Configuración simplificada
        genai.configure(api_key=api_key)
        
        # Inicialización directa del modelo
        model = genai.GenerativeModel('gemini-1.5-flash')

        if st.button('🚀 GENERAR RESUMEN AHORA'):
            with st.spinner('Buscando noticias actuales...'):
                fecha_hoy = datetime.now().strftime('%d/%m/%Y')
                
                # Prompt optimizado
                prompt = f"""
                Hoy es {fecha_hoy}. Busca y resume las noticias de HOY en Bolivia.
                Medios: Opinión, Los Tiempos, La Voz de Tarija y televisión boliviana.
                Temas prioritarios: Economía, Impuestos y Política en Cochabamba y Tarija.
                
                Presenta 6 noticias siguiendo este formato EXACTO:
                
                **TITULAR: [TITULAR EN MAYÚSCULAS Y NEGRITA]**
                **MEDIO: [MEDIO EN MAYÚSCULAS Y NEGRITA]**
                Resumen: [3 a 4 líneas de análisis]
                Enlace: https://directausa.com/
                
                No incluyas introducciones.
                """
                
                # Ejecución
                response = model.generate_content(prompt)
                
                if response.text:
                    st.success("Resumen generado")
                    st.markdown(response.text)
                else:
                    st.error("No se obtuvo respuesta de la IA.")

    except Exception as e:
        st.error("Ocurrió un error al procesar la solicitud.")
        st.info(f"Detalle técnico: {e}")
else:
    st.warning("👈 Por favor, ingresa tu API Key en la barra lateral.")

st.sidebar.markdown("---")
st.sidebar.write("Formato compatible con Word")
 
