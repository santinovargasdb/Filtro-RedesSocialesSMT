from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from config import SMATA_COLORS
import datetime
import io

def generate_docx(posts):
    document = Document()
    
    # Header
    title = document.add_heading('SMATA Social Monitor', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    date_str = datetime.date.today().strftime("%d/%m/%Y")
    subtitle = document.add_paragraph(f"Informe Institucional de Monitoreo de Redes Sociales — {date_str}")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    document.add_paragraph() # Add some space
    
    # Calculate summary
    summary = {"twitter": 0, "instagram": 0, "tiktok": 0}
    for p in posts:
        summary[p["network"]] = summary.get(p["network"], 0) + 1
        
    summary_para = document.add_paragraph()
    summary_para.add_run(f"Total Posts Incluidos: {len(posts)}\n").bold = True
    summary_para.add_run(f"X (Twitter): {summary['twitter']} | ")
    summary_para.add_run(f"Instagram: {summary['instagram']} | ")
    summary_para.add_run(f"TikTok: {summary['tiktok']}")
    
    document.add_page_break()
    
    for post in posts:
        # Post Header
        p_header = document.add_paragraph()
        run_network = p_header.add_run(post.get('network', '').capitalize())
        run_network.bold = True
        run_network.font.color.rgb = RGBColor(0, 150, 0) # approximation for GREEN_LIGHT
        
        p_header.add_run(f" - {post.get('date', '')}")
        
        # Author
        p_author = document.add_paragraph()
        run_author = p_author.add_run(post.get('author', ''))
        run_author.bold = True
        
        # Text
        document.add_paragraph(post.get('text', ''))
        
        # Footer
        p_footer = document.add_paragraph()
        run_score = p_footer.add_run(f"Score: {post.get('relevance_score', 0)}")
        run_score.bold = True
        run_score.font.color.rgb = RGBColor(218, 165, 32) # Gold
        
        terms = ", ".join(post.get('matched_terms', []))
        p_footer.add_run(f" | Matcheó: {terms}")
        
        document.add_paragraph("-" * 40) # separator
        
    # Save to a bytes buffer
    doc_io = io.BytesIO()
    document.save(doc_io)
    doc_io.seek(0)
    
    return doc_io.read()
