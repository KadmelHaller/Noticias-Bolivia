import streamlit as st
import google.generativeai as genai
import feedparser
from datetime import datetime
import pytz
import urllib.parse
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Monitor de Medios | SIN Bolivia",
    layout="wide",
    initial_sidebar_state="expanded"
)

zona_horaria = pytz.timezone('America/La_Paz')
fecha_hoy = datetime.now(zona_horaria)
fecha_hoy_str = fecha_hoy.strftime('%d/%m/%Y')
hora_hoy_str = fecha_hoy.strftime('%H:%M')

# --- ESTILOS CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    .stApp {
        background-color: #0d0d0d;
        color: #e8e8e8;
    }

    h1, h2, h3 {
        font-family: 'IBM Plex Mono', monospace !important;
        letter-spacing: -0.02em;
    }

    .header-bar {
        background: linear-gradient(135deg, #1a1a1a 0%, #111 100%);
        border-left: 4px solid #e63946;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        border-radius: 0 6px 6px 0;
    }

    .header-bar h1 {
        color: #ffffff;
        font-size: 1.6rem;
        margin: 0;
    }

    .header-bar p {
        color: #888;
        margin: 0.2rem 0 0;
        font-size: 0.85rem;
        font-family: 'IBM Plex Mono', monospace;
    }

    /* Tarjetas de noticias */
    .noticia-roja {
        background: #1a0a0a;
        border-left: 4px solid #e63946;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
        border-radius: 0 6px 6px 0;
    }

    .noticia-amarilla {
        background: #1a1500;
        border-left: 4px solid #f4c430;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
        border-radius: 0 6px 6px 0;
    }

    .noticia-verde {
        background: #0a1a0d;
        border-left: 4px solid #2dc653;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
        border-radius: 0 6px 6px 0;
    }

    .badge-roja {
        background: #e63946;
        color: white;
        padding: 2px 10px;
        border-radius: 3px;
        font-size: 0.72rem;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        letter-spacing: 0.05em;
    }

    .badge-amarilla {
        background: #f4c430;
        color: #111;
        padding: 2px 10px;
        border-radius: 3px;
        font-size: 0.72rem;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        letter-spacing: 0.05em;
    }

    .badge-verde {
        background: #2dc653;
        color: #111;
        padding: 2px 10px;
        border-radius: 3px;
        font-size: 0.72rem;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        letter-spacing: 0.05em;
    }

    .noticia-titular {
        font-size: 1rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0.5rem 0 0.3rem;
        line-height: 1.35;
    }

    .noticia-medio {
        font-size: 0.78rem;
        font-family: 'IBM Plex Mono', monospace;
        color: #aaa;
        letter-spacing: 0.04em;
        margin-bottom: 0.4rem;
    }

    .noticia-resumen {
        font-size: 0.88rem;
        color: #ccc;
        line-height: 1.55;
        margin-bottom: 0.5rem;
    }

    .noticia-link a {
        color: #4a9eff !important;
        text-decoration: underline !important;
        font-size: 0.82rem;
        font-family: 'IBM Plex Mono', monospace;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #111 !important;
        border-right: 1px solid #222;
    }

    .sidebar-section {
        background: #1a1a1a;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        margin-bottom: 0.8rem;
        border: 1px solid #2a2a2a;
    }

    .sidebar-section h4 {
        color: #888;
        font-size: 0.72rem;
        font-family: 'IBM Plex Mono', monospace;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin: 0 0 0.5rem;
    }

    .stTextInput input, .stTextArea textarea {
        background-color: #1a1a1a !important;
        border: 1px solid #333 !important;
        color: #e8e8e8 !important;
        font-family: 'IBM Plex Mono', monospace !important;
        border-radius: 4px !important;
    }

    .stButton > button {
        background: #e63946 !important;
        color: white !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 4px !important;
        letter-spacing: 0.04em !important;
        width: 100%;
        padding: 0.6rem 1rem !important;
        transition: opacity 0.2s;
    }

    .stButton > button:hover {
        opacity: 0.85 !important;
    }

    .tab-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
    }

    .stat-box {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 6px;
        padding: 0.7rem 1rem;
        text-align: center;
    }

    .stat-box .num {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.6rem;
        font-weight: 700;
        color: #e8e8e8;
    }

    .stat-box .label {
        font-size: 0.72rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .rss-tag {
        display: inline-block;
        background: #1a1a1a;
        border: 1px solid #333;
        color: #888;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        padding: 2px 8px;
        border-radius: 3px;
        margin: 2px;
    }

    .seccion-titulo {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: #555;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        border-bottom: 1px solid #222;
        padding-bottom: 0.4rem;
        margin-bottom: 1rem;
    }

    /* Quitar el fondo blanco de tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent !important;
        border-bottom: 1px solid #222;
    }

    .stTabs [data-baseweb="tab"] {
        color: #666 !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.82rem !important;
    }

    .stTabs [aria-selected="true"] {
        color: #e8e8e8 !important;
        border-bottom: 2px solid #e63946 !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        background: transparent !important;
        padding: 1rem 0 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #e8e8e8 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. DEFINICIÓN DE FUENTES RSS ---
FUENTES_RSS = {
    "Los Tiempos (Cbba)": "https://www.lostiempos.com/rss",
    "Opinión (Cbba)": "https://www.opinion.com.bo/rss",
    "El Potosí": "https://elpotosi.net/rss",
    "La Patria (Oruro)": "https://www.lapatriaenlinea.com/?rss=1",
    "Google Alerts - SIN": "",  # Se ingresa manualmente
    "Google Alerts - Economía": "",  # Se ingresa manualmente
    "Google Alerts - Política": "",  # Se ingresa manualmente
}

CIUDADES = ["Cochabamba", "Oruro", "Potosí"]

TEMATICAS = {
    "roja": {
        "label": "🔴 SIN / Impuestos",
        "keywords": ["SIN", "Servicio de Impuestos Nacionales", "impuestos", "tributario", "SIAT", "factura", "cobranza coactiva"],
        "color": "roja",
        "badge": "badge-roja",
        "descripcion": "Servicio de Impuestos Nacionales"
    },
    "amarilla": {
        "label": "🟡 Economía / Finanzas",
        "keywords": ["economía", "finanzas", "dólar", "tipo de cambio", "inflación", "deuda", "PIB", "presupuesto", "banco", "crédito"],
        "color": "amarilla",
        "badge": "badge-amarilla",
        "descripcion": "Economía y Finanzas"
    },
    "verde": {
        "label": "🟢 Política",
        "keywords": ["gobierno", "municipio", "alcalde", "gobernación", "político", "elecciones", "asamblea", "concejo"],
        "color": "verde",
        "badge": "badge-verde",
        "descripcion": "Política Regional"
    }
}

# --- 3. MOTOR DE CAPTURA RSS ---
def buscar_noticias_rss(rss_url, nombre_fuente=""):
    """Parsea un feed RSS y devuelve lista de noticias."""
    try:
        feed = feedparser.parse(rss_url)
        hallazgos = []
        for entry in feed.entries:
            titulo = entry.get("title", "Sin título")
            link_crudo = entry.get("link", "")
            resumen = entry.get("summary", entry.get("description", ""))

            # Limpiar URL de redirección de Google Alerts
            if "url?q=" in link_crudo:
                link_limpio = urllib.parse.unquote(link_crudo.split("url?q=")[1].split("&")[0])
            else:
                link_limpio = link_crudo

            # Extraer nombre de medio desde URL
            try:
                medio_url = urllib.parse.urlparse(link_limpio).netloc.replace("www.", "")
            except:
                medio_url = nombre_fuente or "Desconocido"

            hallazgos.append({
                "titular": titulo,
                "link": link_limpio,
                "resumen": resumen[:400] if resumen else "",
                "medio": nombre_fuente or medio_url,
            })
        return hallazgos
    except Exception as e:
        return []

def clasificar_noticia(titular, resumen):
    """Clasifica una noticia en una temática según palabras clave."""
    texto = (titular + " " + resumen).lower()
    for tema_key, tema in TEMATICAS.items():
        for kw in tema["keywords"]:
            if kw.lower() in texto:
                return tema_key
    return "verde"  # Default: política/interés general

# --- 4. ANALISTA IA (GEMINI) ---
def procesar_con_ia(noticias_raw, api_key, ciudad_filtro=None):
    """
    Envía las noticias a Gemini para análisis estructurado.
    Devuelve lista de dicts con: titular, medio, resumen, link, categoria.
    """
    genai.configure(api_key=api_key)
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_id = next((m for m in modelos if "flash" in m), modelos[0])
    except Exception as e:
        st.error(f"Error conectando con Gemini: {e}")
        return []

    model = genai.GenerativeModel(modelo_id)

    ciudades_str = ", ".join(CIUDADES)
    resultados = []
    total_lotes = (len(noticias_raw) + 4) // 5

    progress = st.progress(0, text="Analizando con IA...")

    for i in range(0, len(noticias_raw), 5):
        lote = noticias_raw[i:i+5]
        bloque = "\n".join([
            f"ID:{j+1} | TITULAR: {n['titular']} | MEDIO: {n['medio']} | RESUMEN: {n['resumen'][:200]} | URL: {n['link']}"
            for j, n in enumerate(lote)
        ])

        prompt = f"""
Eres un analista de medios boliviano experto. Fecha: {fecha_hoy_str}.
Ciudades de interés: {ciudades_str}.

Analiza estas noticias y para CADA UNA devuelve un bloque con este formato EXACTO (sin cambiar los delimitadores):

===NOTICIA_START===
CATEGORIA: [ROJA|AMARILLA|VERDE]
TITULAR: [titular en mayúsculas, exacto]
MEDIO: [nombre del medio en mayúsculas]
RESUMEN: [resumen periodístico de 3-5 líneas, contexto boliviano]
URL: [url exacta sin modificar]
===NOTICIA_END===

Categorías:
- ROJA: SIN (Servicio de Impuestos Nacionales), tributario, impuestos, fiscalización
- AMARILLA: economía, finanzas, dólar, inflación, bancos, comercio, deuda
- VERDE: política local/regional, gobernación, municipio, asamblea, alcaldes

Si la noticia no es relevante para {ciudades_str} ni para las temáticas, ponla en VERDE con resumen breve.

NOTICIAS A ANALIZAR:
{bloque}
"""
        try:
            res = model.generate_content(prompt)
            texto = res.text

            # Parsear bloques estructurados
            bloques = texto.split("===NOTICIA_START===")
            for bloque_txt in bloques[1:]:
                bloque_txt = bloque_txt.split("===NOTICIA_END===")[0].strip()
                noticia_parsed = {}
                for linea in bloque_txt.split("\n"):
                    if linea.startswith("CATEGORIA:"):
                        noticia_parsed["categoria"] = linea.replace("CATEGORIA:", "").strip().lower()
                    elif linea.startswith("TITULAR:"):
                        noticia_parsed["titular"] = linea.replace("TITULAR:", "").strip()
                    elif linea.startswith("MEDIO:"):
                        noticia_parsed["medio"] = linea.replace("MEDIO:", "").strip()
                    elif linea.startswith("RESUMEN:"):
                        noticia_parsed["resumen"] = linea.replace("RESUMEN:", "").strip()
                    elif linea.startswith("URL:"):
                        noticia_parsed["link"] = linea.replace("URL:", "").strip()

                if "titular" in noticia_parsed:
                    # Normalizar categoría
                    cat = noticia_parsed.get("categoria", "verde")
                    if cat not in ["roja", "amarilla", "verde"]:
                        cat = "verde"
                    noticia_parsed["categoria"] = cat
                    resultados.append(noticia_parsed)

            time.sleep(1.5)
        except Exception as e:
            # Fallback: agregar sin IA
            for n in lote:
                n["categoria"] = clasificar_noticia(n["titular"], n["resumen"])
                resultados.append(n)

        lote_num = (i // 5) + 1
        progress.progress(lote_num / total_lotes, text=f"Procesando lote {lote_num} de {total_lotes}...")

    progress.empty()
    return resultados

# --- 5. RENDERIZADO DE NOTICIAS ---
def render_noticia(n):
    """Renderiza una tarjeta de noticia con el formato solicitado."""
    cat = n.get("categoria", "verde")
    tema = TEMATICAS.get(cat, TEMATICAS["verde"])
    clase_card = f"noticia-{tema['color']}"
    clase_badge = tema["badge"]
    label_badge = tema["descripcion"].upper()

    titular = n.get("titular", "Sin título")
    medio = n.get("medio", "MEDIO DESCONOCIDO").upper()
    resumen = n.get("resumen", "Sin resumen disponible.")
    link = n.get("link", "#")

    st.markdown(f"""
    <div class="{clase_card}">
        <span class="{clase_badge}">{label_badge}</span>
        <div class="noticia-titular">{titular}</div>
        <div class="noticia-medio">{medio}</div>
        <div class="noticia-resumen">{resumen}</div>
        <div class="noticia-link"><a href="{link}" target="_blank">🔗 Ver nota completa</a></div>
    </div>
    """, unsafe_allow_html=True)

# --- 6. ENLACES A REDES SOCIALES ---
def render_redes_sociales():
    st.markdown('<div class="seccion-titulo">Monitoreo en redes sociales</div>', unsafe_allow_html=True)

    terminos = {
        "SIN Bolivia": "SIN impuestos Bolivia",
        "Economía Cbba": "economía Cochabamba Bolivia",
        "Economía Oruro": "economía Oruro Bolivia",
        "Economía Potosí": "economía Potosí Bolivia",
        "Política Cbba": "Cochabamba política Bolivia",
        "Política Oruro": "Oruro política Bolivia",
        "Política Potosí": "Potosí política Bolivia",
    }

    redes = {
        "Facebook": "facebook.com",
        "X (Twitter)": "x.com OR twitter.com",
        "TikTok": "tiktok.com",
        "Instagram": "instagram.com",
        "YouTube": "youtube.com",
    }

    tab_24h, tab_1h, tab_7d = st.tabs(["Últimas 24h", "Última hora", "Última semana"])

    for tab, tbs in [(tab_24h, "qdr:d"), (tab_1h, "qdr:h"), (tab_7d, "qdr:w")]:
        with tab:
            cols = st.columns(len(redes))
            for col, (red_nombre, red_site) in zip(cols, redes.items()):
                with col:
                    st.markdown(f"**{red_nombre}**")
                    for termino, query in terminos.items():
                        q = urllib.parse.quote(f'site:{red_site} "{query}"')
                        st.markdown(f"[{termino}](https://www.google.com/search?q={q}&tbs={tbs})")

# --- 7. INTERFAZ PRINCIPAL ---

# Header
st.markdown(f"""
<div class="header-bar">
    <h1>MONITOR DE MEDIOS — BOLIVIA</h1>
    <p>Cochabamba · Oruro · Potosí &nbsp;|&nbsp; {fecha_hoy_str} {hora_hoy_str} &nbsp;|&nbsp; SIN · Economía · Política</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuración")

    st.markdown('<div class="sidebar-section"><h4>API de Inteligencia Artificial</h4>', unsafe_allow_html=True)
    api_key = st.text_input("API Key Gemini:", type="password", placeholder="AIza...")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section"><h4>Feeds RSS — Google Alerts</h4>', unsafe_allow_html=True)
    rss_sin = st.text_input("🔴 RSS — SIN / Impuestos:", placeholder="https://www.google.com/alerts/feeds/...")
    rss_economia = st.text_input("🟡 RSS — Economía / Finanzas:", placeholder="https://www.google.com/alerts/feeds/...")
    rss_politica = st.text_input("🟢 RSS — Política:", placeholder="https://www.google.com/alerts/feeds/...")
    rss_extra = st.text_input("➕ RSS adicional (opcional):", placeholder="URL de otro feed RSS")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section"><h4>Opciones</h4>', unsafe_allow_html=True)
    usar_ia = st.toggle("Análisis con IA (Gemini)", value=True)
    st.markdown('</div>', unsafe_allow_html=True)

    iniciar = st.button("🚀 INICIAR MONITOREO")

# Pestañas principales
tab_noticias, tab_redes, tab_ayuda = st.tabs([
    "📰 Noticias de Medios",
    "📱 Redes Sociales",
    "❓ Cómo configurar"
])

# --- TAB 1: NOTICIAS ---
with tab_noticias:
    if iniciar:
        # Recolectar feeds configurados
        feeds_a_procesar = []
        if rss_sin:
            feeds_a_procesar.append(("Google Alerts — SIN", rss_sin))
        if rss_economia:
            feeds_a_procesar.append(("Google Alerts — Economía", rss_economia))
        if rss_politica:
            feeds_a_procesar.append(("Google Alerts — Política", rss_politica))
        if rss_extra:
            feeds_a_procesar.append(("Fuente adicional", rss_extra))

        if not feeds_a_procesar:
            st.warning("⚠️ Ingresa al menos una URL de feed RSS en la barra lateral.")
        elif usar_ia and not api_key:
            st.error("❌ Ingresa tu API Key de Gemini para usar el análisis con IA.")
        else:
            # Captura de noticias
            todas_noticias = []
            with st.spinner("Capturando noticias de los feeds..."):
                for nombre, url in feeds_a_procesar:
                    noticias = buscar_noticias_rss(url, nombre)
                    todas_noticias.extend(noticias)

            if not todas_noticias:
                st.warning("No se encontraron noticias en los feeds ingresados. Verifica las URLs.")
            else:
                # Análisis IA o clasificación local
                if usar_ia and api_key:
                    noticias_procesadas = procesar_con_ia(todas_noticias, api_key)
                else:
                    noticias_procesadas = []
                    for n in todas_noticias:
                        n["categoria"] = clasificar_noticia(n["titular"], n["resumen"])
                        noticias_procesadas.append(n)

                # Guardar en sesión
                st.session_state["noticias"] = noticias_procesadas

    # Mostrar resultados (persiste aunque no se vuelva a hacer clic)
    if "noticias" in st.session_state and st.session_state["noticias"]:
        noticias_procesadas = st.session_state["noticias"]

        # Separar por categoría
        rojas = [n for n in noticias_procesadas if n.get("categoria") == "roja"]
        amarillas = [n for n in noticias_procesadas if n.get("categoria") == "amarilla"]
        verdes = [n for n in noticias_procesadas if n.get("categoria") == "verde"]

        # Estadísticas
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="stat-box"><div class="num">{len(noticias_procesadas)}</div><div class="label">Total noticias</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-box"><div class="num" style="color:#e63946">{len(rojas)}</div><div class="label">🔴 SIN / Impuestos</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-box"><div class="num" style="color:#f4c430">{len(amarillas)}</div><div class="label">🟡 Economía</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="stat-box"><div class="num" style="color:#2dc653">{len(verdes)}</div><div class="label">🟢 Política</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Tabs por categoría
        tab_r, tab_a, tab_v, tab_todas = st.tabs([
            f"🔴 SIN / Impuestos ({len(rojas)})",
            f"🟡 Economía ({len(amarillas)})",
            f"🟢 Política ({len(verdes)})",
            f"📋 Todas ({len(noticias_procesadas)})"
        ])

        with tab_r:
            if rojas:
                for n in rojas:
                    render_noticia(n)
            else:
                st.info("No se encontraron noticias en esta categoría.")

        with tab_a:
            if amarillas:
                for n in amarillas:
                    render_noticia(n)
            else:
                st.info("No se encontraron noticias en esta categoría.")

        with tab_v:
            if verdes:
                for n in verdes:
                    render_noticia(n)
            else:
                st.info("No se encontraron noticias en esta categoría.")

        with tab_todas:
            for n in noticias_procesadas:
                render_noticia(n)

        # Exportar como texto
        with st.expander("📄 Exportar reporte en texto"):
            reporte_txt = f"MONITOR DE MEDIOS BOLIVIA — {fecha_hoy_str} {hora_hoy_str}\n"
            reporte_txt += "=" * 60 + "\n\n"
            for cat_key, cat_noticias in [("ROJA (SIN)", rojas), ("AMARILLA (ECONOMÍA)", amarillas), ("VERDE (POLÍTICA)", verdes)]:
                if cat_noticias:
                    reporte_txt += f"\n{'─'*40}\n⬛ CATEGORÍA {cat_key}\n{'─'*40}\n\n"
                    for n in cat_noticias:
                        reporte_txt += f"**{n.get('titular','').upper()}**\n"
                        reporte_txt += f"**{n.get('medio','').upper()}**\n"
                        reporte_txt += f"{n.get('resumen','')}\n"
                        reporte_txt += f"{n.get('link','')}\n"
                        reporte_txt += "---\n\n"
            st.text_area("Reporte:", value=reporte_txt, height=400)

    elif not iniciar:
        st.markdown("""
        <div style="text-align:center; padding: 4rem 2rem; color: #444;">
            <div style="font-size:2.5rem; margin-bottom:1rem;">📡</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.9rem;">
                Configura los feeds RSS en la barra lateral<br>y presiona <strong>INICIAR MONITOREO</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 2: REDES SOCIALES ---
with tab_redes:
    render_redes_sociales()

# --- TAB 3: AYUDA ---
with tab_ayuda:
    st.markdown("### Cómo configurar el monitoreo")

    st.markdown("""
    #### 1. Obtener una API Key de Gemini (gratis)
    1. Ve a [aistudio.google.com](https://aistudio.google.com)
    2. Inicia sesión con tu cuenta de Google
    3. Haz clic en **"Get API key"** → **"Create API key"**
    4. Copia la clave y pégala en la barra lateral

    #### 2. Crear alertas en Google Alerts
    1. Ve a [google.com/alerts](https://www.google.com/alerts)
    2. Crea tres alertas con estos términos:
       - `"Servicio de Impuestos Nacionales" OR "SIN Bolivia" OR impuestos Cochabamba OR impuestos Oruro OR impuestos Potosí`
       - `economía Cochabamba OR economía Oruro OR economía Potosí OR finanzas Bolivia`
       - `política Cochabamba OR Oruro gobernación OR Potosí municipio`
    3. En cada alerta, selecciona **"RSS"** como formato de entrega
    4. Copia el enlace RSS y pégalo en la barra lateral

    #### 3. Formato de las noticias
    Cada noticia se muestra con:
    - 🔴 **Rojo**: SIN / Impuestos Nacionales
    - 🟡 **Amarillo**: Economía y finanzas
    - 🟢 **Verde**: Política e interés general

    #### 4. Redes sociales
    La pestaña **Redes Sociales** genera búsquedas automáticas en Google
    para encontrar publicaciones recientes en Facebook, X, TikTok, Instagram y YouTube.
    """)
