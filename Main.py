import streamlit as st
import google.generativeai as genai
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="IA News Bolivia", page_icon="🇧🇴")

st.title("🤖 RESUMEN INTELIGENTE: COCHABAMBA Y BOLIVIA")
st.markdown("Generado por Gemini con fuentes de Opinión, Los Tiempos, La Voz de Tarija y TV.")

# Entrada para tu API Key
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # Cambiado a 'gemini-1.5-flash' sin sufijos de versión beta para evitar el 404
        model = genai.GenerativeModel('gemini-1.5-flash')

        if st.button('🚀 GENERAR RESUMEN AHORA'):
            with st.spinner('Buscando y resumiendo noticias...'):
                fecha_hoy = datetime.now().strftime('%d de %m de %y')
                
                prompt = f"""
                Actúa como un analista de noticias senior en Bolivia. Hoy es {fecha_hoy}.
                Tu tarea es buscar información real de hoy en los portales web de:
                1. Los Tiempos (Cochabamba)
                2. Opinión (Cochabamba)
                3. La Voz de Tarija
                4. Redes de TV (Unitel, Red Uno, Bolivia TV) sobre la coyuntura en Cochabamba.

                Filtra solo noticias de ECONOMÍA, IMPUESTOS y POLÍTICA.
                
                Presenta 6 noticias siguiendo este formato EXACTO para que yo pueda copiarlo a Word:

                **TITULAR: [TITULAR EN MAYÚSCULAS Y NEGRITA]**
                **MEDIO: [NOMBRE DEL MEDIO EN MAYÚSCULAS Y NEGRITA]**
                Resumen: [Un párrafo de 3 a 4 líneas con datos concretos y cifras si existen]
                Enlace: https://x.com/LaRealnoticia

                No incluyas saludos ni despedidas, solo el contenido.
                """
                
                # Generación de contenido
                response = model.generate_content(prompt)
                
                if response.text:
                    st.success(f"Resumen generado exitosamente")
                    st.markdown(response.text)
                    st.download_button("Descargar como Texto para Word", response.text, file_name=f"noticias_{fecha_hoy}.txt")
                
    except Exception as e:
        st.error(f"Error en la aplicación: {e}")
else:
    st.warning("👈 Ingresa tu API Key en la barra lateral. Si no tienes una, obtenla en aistudio.google.com")

st.sidebar.markdown("---")
st.sidebar.info("Tip: Si el error persiste, asegúrate de que tu cuenta de Google Cloud tiene habilitada la API de Generative Language.")
            
            try:
                response = model.generate_content(prompt)
                
                # Mostrar el resultado
                st.success(f"Resumen generado el {datetime.now().strftime('%H:%M')}")
                st.markdown(response.text)
                
                st.info("💡 Puedes copiar este texto directamente a tu documento Word.")
                
            except Exception as e:
                st.error(f"Error al conectar con Gemini: {e}")
else:
    st.warning("👈 Por favor, ingresa tu API Key de Gemini en la barra lateral para comenzar.")

st.sidebar.markdown("---")
st.sidebar.write("Diseñado para exportar a Word - Formato Mayo 2026")
