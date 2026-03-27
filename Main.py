from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import os

def generar_word_exacto(texto, ciudad_tag):
    doc = Document()
    
    # --- CONFIGURACIÓN DE FUENTE GLOBAL (Times New Roman 10) ---
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(10)
    # Forzar que Word reconozca la fuente correctamente
    r = style.element.rPr.rFonts
    r.set(qn('w:ascii'), 'Times New Roman')
    r.set(qn('w:hAnsi'), 'Times New Roman')

    # --- ENCABEZADO CON LOGO ---
    section = doc.sections[0]
    header = section.header
    header_para = header.paragraphs[0]
    header_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    # Intentar cargar el logo (debes subir un archivo llamado logo.png a tu repo)
    if os.path.exists("logo.png"):
        run_logo = header_para.add_run()
        run_logo.add_picture("logo.png", width=Inches(1.5))
    
    # --- DATOS DE ENVÍO ---
    doc.add_paragraph("N°")
    doc.add_paragraph(fecha_hoy)
    doc.add_paragraph(obtener_info_envio())
    doc.add_paragraph("") # Espacio en blanco

    # --- FILTRADO POR CIUDAD Y FORMATO ---
    target = "COCHABAMBA" if ciudad_tag == "CBBA" else "SANTA CRUZ"
    lineas = texto.split('\n')
    capturando = False
    
    for linea in lineas:
        # Detectar sección de la ciudad
        if target in linea.upper() and ("1." in linea or "2." in linea):
            capturando = True
            continue
        # Detener captura si empieza la otra ciudad
        if capturando and any(x in linea.upper() for x in ["1. COCHABAMBA", "2. SANTA CRUZ"]) and target not in linea.upper():
            capturando = False
            
        if capturando and linea.strip():
            p = doc.add_paragraph()
            
            # Formato de Titular (Mayúsculas y Negrita)
            if linea.startswith('*') and linea.endswith('*'):
                run = p.add_run(linea.replace('*', '').upper())
                run.bold = True
            
            # Formato de Medio de Comunicación (Negrita según tu nuevo requerimiento)
            elif any(medio in linea.upper() for medio in ["OPINIÓN", "LOS TIEMPOS", "UNITEL", "RED UNO", "EL DEBER", "LA VOZ", "VISIÓN 360", "ATB", "PAT", "BOLIVIA TV"]):
                run = p.add_run(linea.upper())
                run.bold = True
            
            # Resumen y Links (Texto Normal)
            else:
                p.add_run(linea)
            
            # Añadir un pequeño espacio entre elementos para que no se vea amontonado
            p.paragraph_format.space_after = Pt(6)

    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()
