from weasyprint import HTML
from jinja2 import Template
from config import SMATA_COLORS
import datetime

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: 'Inter', sans-serif; color: #333; margin: 0; padding: 40px; }
        .header { border-bottom: 3px solid {{ colors.GREEN_DARK }}; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: {{ colors.GREEN_DARK }}; margin: 0; font-size: 24px; }
        .header p { color: #666; margin: 5px 0 0; }
        .summary { background: {{ colors.GREEN_PALE }}; padding: 20px; border-radius: 8px; margin-bottom: 30px; display: flex; justify-content: space-between; }
        .summary-item { text-align: center; }
        .summary-item .value { display: block; font-size: 20px; font-weight: bold; color: {{ colors.GREEN_MID }}; }
        .summary-item .label { font-size: 12px; color: #666; text-transform: uppercase; }
        .post { margin-bottom: 25px; border: 1px solid #eee; padding: 15px; border-radius: 8px; page-break-inside: avoid; }
        .post-header { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px; }
        .post-network { font-weight: bold; text-transform: capitalize; color: {{ colors.GREEN_LIGHT }}; }
        .post-date { color: #999; }
        .post-author { font-weight: bold; color: #444; margin-bottom: 8px; }
        .post-text { font-size: 14px; line-height: 1.5; margin-bottom: 10px; }
        .post-footer { display: flex; align-items: center; gap: 10px; }
        .score { font-size: 12px; font-weight: bold; padding: 4px 8px; border-radius: 4px; background: {{ colors.GOLD }}; }
        .terms { font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>SMATA Social Monitor</h1>
        <p>Informe Institucional de Monitoreo de Redes Sociales — {{ date }}</p>
    </div>

    <div class="summary">
        <div class="summary-item">
            <span class="value">{{ posts|length }}</span>
            <span class="label">Posts Incluidos</span>
        </div>
        <div class="summary-item">
            <span class="value">{{ summary.twitter }}</span>
            <span class="label">X (Twitter)</span>
        </div>
        <div class="summary-item">
            <span class="value">{{ summary.instagram }}</span>
            <span class="label">Instagram</span>
        </div>
        <div class="summary-item">
            <span class="value">{{ summary.tiktok }}</span>
            <span class="label">TikTok</span>
        </div>
    </div>

    {% for post in posts %}
    <div class="post">
        <div class="post-header">
            <span class="post-network">{{ post.network }}</span>
            <span class="post-date">{{ post.date }}</span>
        </div>
        <div class="post-author">{{ post.author }}</div>
        <div class="post-text">{{ post.text }}</div>
        <div class="post-footer">
            <span class="score">Score: {{ post.relevance_score }}</span>
            <span class="terms">Matcheó: {{ post.matched_terms|join(', ') }}</span>
        </div>
    </div>
    {% endfor %}
</body>
</html>
"""

def generate_pdf(posts):
    template = Template(HTML_TEMPLATE)
    
    # Calculate summary
    summary = {"twitter": 0, "instagram": 0, "tiktok": 0}
    for p in posts:
        summary[p["network"]] = summary.get(p["network"], 0) + 1
        
    html_content = template.render(
        posts=posts,
        colors=SMATA_COLORS,
        date=datetime.date.today().strftime("%d/%m/%Y"),
        summary=summary
    )
    
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes
