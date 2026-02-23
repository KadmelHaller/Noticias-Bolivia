import streamlit as st

st.title("📰 MI GENERADOR DE NOTICIAS")

def generar():
    # Aquí es donde pondrías la lógica de búsqueda real
    return [
        {"titular": "FEPC PRESENTA PROYECTOS ESTRATÉGICOS PARA COCHABAMBA", "medio": "OPINIÓN", "resumen": "Propuesta de infraestructura vial y logística.", "link": "https://www.opinion.com.bo/noticia1"},
        {"titular": "ELIMINACIÓN DEL ITF BUSCA DINAMIZAR EL DÓLAR", "medio": "LOS TIEMPOS", "resumen": "Medida económica aprobada en Diputados.", "link": "https://www.lostiempos.com/noticia2"}
    ]

if st.button('PRESIONA PARA GENERAR RESUMEN'):
    noticias = generar()
    for n in noticias:
        # Formato solicitado: NEGRITA Y MAYÚSCULAS
        st.markdown(f"**TITULAR: {n['titular'].upper()}**")
        st.markdown(f"**MEDIO: {n['medio'].upper()}**")
        st.write(f"Resumen: {n['resumen']}")
        st.write(f"Enlace: {n['link']}")
        st.write("---")
 
