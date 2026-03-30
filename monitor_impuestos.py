import streamlit as st
from googlesearch import search

def run_impuestos_monitor():
    st.subheader("🔍 Monitoreo de Influencers: Impuestos Bolivia")
    st.caption("Resultados de las últimas 24 horas")

    queries = [
        '"impuestos" "Cochabamba" site:facebook.com',
        '"impuestos" "Cochabamba" site:x.com',
        '"impuestos" "Cochabamba" site:instagram.com',
        '"impuestos" "Cochabamba" site:tiktok.com',
        '"impuestos" "Santa Cruz" site:facebook.com',
        '"impuestos" "Santa Cruz" site:x.com',
        '"impuestos" "Santa Cruz" site:instagram.com',
        '"impuestos" "Santa Cruz" site:tiktok.com'
    ]

    if st.button("Iniciar Rastreo de Impuestos"):
        resultados_encontrados = []
        with st.spinner("Rastreando redes sociales..."):
            for q in queries:
                try:
                    # 'tbs':'qdr:d' es el parámetro para las últimas 24h
                    for res in search(q, lang="es", num=5, stop=5, pause=2, extra_params={'tbs': 'qdr:d'}):
                        # Filtro básico para evitar ruido
                        blacklist = ["oferta", "precio", "vendo", "noticiero", "diario", "curso", "taller", "inscripciones"]
                        if not any(word in res.lower() for word in blacklist):
                            resultados_encontrados.append(res)
                except Exception as e:
                    st.error(f"Error en {q.split('site:')[1]}: {e}")

        links = list(set(resultados_encontrados))
        
        if not links:
            st.warning("No se encontraron noticias (influencers) en las últimas 24 horas.")
        else:
            st.success(f"Se detectaron {len(links)} posibles menciones.")
            for link in links:
                st.markdown(f"📌 **Posible Opinión:** [Ver Publicación]({link})")
