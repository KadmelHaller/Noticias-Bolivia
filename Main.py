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
        # CONFIGURACIÓN CRÍTICA: Forzamos la versión v1 de la API
        genai.configure(
            api_key=api_key,
            client_options={'api_version': 'v1'}
        )
        
        # Usamos el modelo más estándar disponible
        model = genai.GenerativeModel('gemini-1.5-flash')

        if st.button('🚀 GENERAR RESUMEN AHORA'):
            with st.spinner('Accediendo a la red y analizando noticias...'):
                fecha_hoy = datetime.now().strftime('%d/%m/%Y')
                
                prompt = f"""
                Hoy es {fecha_hoy}. Actúa como un buscador de noticias en tiempo real.
                Busca noticias de HOY en Bolivia, específicamente Cochabamba y Tarija.
                FUENTES: Los Tiempos, Opinión, La Voz de Tarija y TV (Unitel, Red Uno).
                TEMAS: Economía, Impuestos y Política.
                
                ENTREGA 6 NOTICIAS CON ESTE FORMATO EXACTO:
                
                **TITULAR: [TITULAR EN MAYÚSCULAS Y NEGRITA]**
                **MEDIO: [MEDIO EN MAYÚSCULAS Y NEGRITA]**
                Resumen: [3 a 4 líneas de análisis]
                Enlace: https://directausa.com/
                
                No incluyas introducciones ni despedidas.
                """
                
                # Llamada a la generación
                response = model.generate_content(prompt)
                
                if response:
                    st.success("Resumen generado con éxito")
                    st.markdown(response.text)
                else:
                    st.error("La IA no devolvió datos.")

    except Exception as e:
        st.error("Error de conexión.")
        st.info(f"Detalle técnico corregido: {e}")
        st.write("Si el error 404 persiste, intenta crear una nueva API Key en Google AI Studio.")
else:
    st.warning("👈 Ingresa tu API Key en la barra lateral.")

st.sidebar.markdown("---")
st.sidebar.write("Formato compatible con Microsoft Word")
