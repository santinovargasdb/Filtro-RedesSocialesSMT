from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import datetime
import io

def generate_docx(posts):
    document = Document()
    
    # TÍTULO PRINCIPAL: TENDENCIA EN REDES (Centrado y destacado)
    title_p = document.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_before = Pt(12)
    title_p.paragraph_format.space_after = Pt(24)
    
    title_run = title_p.add_run("TENDENCIA EN REDES")
    title_run.font.name = 'Arial'
    title_run.font.size = Pt(26)
    title_run.bold = True
    title_run.font.color.rgb = RGBColor(40, 90, 60) # Verde opaco institucional
    
    # Mapeo de las redes en el orden del informe físico
    networks_keys = [("twitter", "X"), ("instagram", "INSTAGRAM"), ("tiktok", "TIK TOK")]
    
    for net_id, net_title in networks_keys:
        # Filtramos los posts pertenecientes a esta red social
        net_posts = [p for p in posts if p.get("network", "").lower() == net_id]
        
        # Nombre de la Red Social (X, INSTAGRAM, TIK TOK) en Negro
        h_p = document.add_paragraph()
        h_p.paragraph_format.space_before = Pt(18)
        h_p.paragraph_format.space_after = Pt(6)
        
        h_run = h_p.add_run(net_title)
        h_run.font.name = 'Arial'
        h_run.font.size = Pt(16)
        h_run.bold = True
        h_run.font.color.rgb = RGBColor(0, 0, 0)
        
        if not net_posts:
            none_p = document.add_paragraph()
            none_run = none_p.add_run("Sin publicaciones destacadas en este período.")
            none_run.font.name = 'Arial'
            none_run.font.italic = True
            none_run.font.size = Pt(10)
            continue
            
        for post in net_posts:
            # Título de la publicación en MAYÚSCULAS y color ROJO
            txt_p = document.add_paragraph()
            txt_p.paragraph_format.space_before = Pt(6)
            txt_p.paragraph_format.space_after = Pt(2)
            
            clean_text = post.get("text", "").upper()
            txt_run = txt_p.add_run(clean_text)
            txt_run.font.name = 'Arial'
            txt_run.font.size = Pt(11)
            txt_run.bold = True
            txt_run.font.color.rgb = RGBColor(180, 20, 20) # Rojo Prensa
            
            # Link directo de la publicación abajo en AZUL y subrayado
            link_p = document.add_paragraph()
            link_p.paragraph_format.space_before = Pt(0)
            link_p.paragraph_format.space_after = Pt(10)
            
            url = post.get("post_url") or "https://x.com"
            link_run = link_p.add_run(url)
            link_run.font.name = 'Arial'
            link_run.font.size = Pt(10)
            link_run.font.underline = True
            link_run.font.color.rgb = RGBColor(30, 85, 150) # Azul Hipervínculo
            
    # Guardamos en el buffer de memoria para la descarga
    doc_io = io.BytesIO()
    document.save(doc_io)
    doc_io.seek(0)
    
    return doc_io.read()
