import streamlit as st
import google.generativeai as genai
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="IA News Bolivia", page_icon="🤖")

# Título visual
st.title("🤖 RESUMEN INTELIGENTE: COCHABAMBA Y BOLIVIA")
st.markdown("Generado por Gemini con fuentes de Opinión, Los Tiempos y TV Boliviana.")

# Entrada para tu API Key (puedes pegarla aquí o configurarla en Secrets de Streamlit)
api_key = st.sidebar.text_input("Pega tu Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    if st.button('🚀 GENERAR RESUMEN CON IA'):
        with st.spinner('Gemini está analizando las noticias de hoy...'):
            # El prompt es la instrucción que recibe la IA
            prompt = f"""
            Hoy es {datetime.now().strftime('%d/%m/%Y')}. 
            Busca noticias actuales de Bolivia, específicamente de Cochabamba y Tarija. 
            Fuentes: Diarios Opinión, Los Tiempos, La Voz de Tarija y reportes de TV (Unitel, Red Uno, Bolivia TV).
            Temas obligatorios: Economía, Impuestos y Política.
            
            Entrégame un resumen de las 6 noticias más importantes siguiendo ESTRICTAMENTE este formato para cada una:
            
            **TITULAR: [ESCRIBE EL TITULAR EN MAYÚSCULAS]**
            **MEDIO: [NOMBRE DEL MEDIO EN MAYÚSCULAS]**
            Resumen: [Escribe un resumen analítico de 3 a 4 líneas]
            Enlace: https://directa.cat/
            
            No añadidas introducciones, solo las noticias con ese formato.
            """
            
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
