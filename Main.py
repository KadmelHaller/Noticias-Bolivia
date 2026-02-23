import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pytz # Librería para asegurar la hora exacta de Bolivia

# 1. Configuración de la página
st.set_page_config(page_title="IA News Bolivia Pro", page_icon="🇧🇴")

# 2. Obtener fecha actual de Bolivia automáticamente
zona_horaria = pytz.timezone('America/La_Paz')
fecha_actual = datetime.now(zona_horaria)
fecha_texto = fecha_actual.strftime('%A %d de %B de %Y') # Ej: Lunes 23 de Febrero de 2026

st.title("📰 RESUMEN DE NOTICIAS BOLIVIA")
st.caption(f"Hoy es: {fecha_texto}")

# 3. Barra lateral para API Key
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # Selección automática del mejor modelo disponible
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_id = next((m for m in models if "flash" in m), models[0])
        
        # INSTRUCCIÓN DINÁMICA: La IA se actualiza cada vez que presionas el botón
        model = genai.GenerativeModel(
            model_name=model_id,
            system_instruction=f"Eres un analista de noticias en tiempo real. HOY ES {fecha_texto}. Tu misión es informar objetivamente sobre Bolivia."
        )

        if st.button('🚀 GENERAR RESUMEN DEL DÍA'):
            with st.spinner(f'Buscando noticias reales del {fecha_texto}...'):
                
                # Prompt que obliga a buscar en los portales específicos con la fecha actual
                prompt = f"""
                Realiza una búsqueda web exhaustiva para encontrar noticias publicadas HOY {fecha_texto}.
                
                FUENTES REQUERIDAS:
                - Periódico Los Tiempos (Cochabamba)
                - Periódico Opinión (Cochabamba)
                - Periódico La Voz de Tarija (Tarija) 
                - Noticieros de TV: Unitel y Red Uno
                
                TEMAS ESPECÍFICOS: Economía, Impuestos y Política.
                
                PRESENTA 5 a 7 NOTICIAS CON ESTE FORMATO (PARA COPIAR A WORD):
                
                **[TITULAR EN MAYÚSCULAS Y NEGRITA]**
                Siguiente línea:
                **[NOMBRE DEL MEDIO EN MAYÚSCULAS Y NEGRITA]**
                Siguiente linea:
                Resumen: [Redacta un resumen analítico de 4 a 5 líneas]
                Siguiente línea:
                Enlace real completo de la noticia
                
                Importante: No inventes datos. Si una noticia es de ayer pero sigue siendo tendencia hoy, puedes incluirla aclarando la fecha. No menciones años pasados como el presente.
                """
                
                response = model.generate_content(prompt)
                
                st.success(f"Resultados para el {fecha_texto}")
                st.markdown(response.text)
                
                # Opción para copiar rápido
                st.button("Re-generar si los enlaces no cargan")

    except Exception as e:
        st.error("Error en la conexión inteligente")
        st.info(f"Detalle: {e}")
else:
    st.warning("👈 Ingresa tu API Key para activar la búsqueda.")

st.sidebar.markdown("---")
st.sidebar.write("App Automatizada 2026")
