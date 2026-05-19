from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from apify_fetcher import fetch_posts  
from docx_generator import generate_docx  # Importa tu archivo de Word ya existente
from collections import Counter
import io
import os

app = FastAPI()

# ========================================================
# 1. CONFIGURACIÓN DE CORS MIDDLEWARE (Siempre arriba de todo)
# ========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Abre los permisos para el dominio de Vercel
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ========================================================
# 2. MODELOS DE DATOS
# ========================================================
class SearchRequest(BaseModel):
    networks: List[str]
    keywords: List[str]
    hashtags: List[str]
    accounts: List[str]
    date_since: Optional[str] = None

class DocumentRequest(BaseModel):
    posts: List[dict]

# ========================================================
# 3. RUTAS Y ENDPOINTS
# ========================================================
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend de Filtro de Redes Sociales corriendo perfectamente"}
    
@app.post("/api/search")
async def search_endpoint(request: SearchRequest):
    try:
        results = fetch_posts(
            networks=request.networks,
            keywords=request.keywords,
            hashtags=request.hashtags,
            accounts=request.accounts,
            date_since=request.date_since
        )

        # Armar resumen de métricas para el Frontend
        by_network = Counter(p["network"] for p in results)
        all_terms = [term for p in results for term in p.get("matched_terms", [])]
        top_keywords = [term for term, _ in Counter(all_terms).most_common(5)]

        # Devolvemos una estructura duplicada súper segura para que no falle el frontend
        return {
            "status": "success",
            "data": results,   # Formato clásico
            "posts": results,  # Formato alternativo
            "summary": {
                "total": len(results),
                "by_network": dict(by_network),
                "top_keywords": top_keywords,
            }
        }
    except Exception as e:
        print(f"Error interno en search: {e}")
        return {"status": "error", "message": str(e)}

# ENDPOINT STRATEGICO: Se llama igual que la petición del front para evitar el 404
# pero por dentro procesa y devuelve el archivo de Word de SMATA (.docx)
@app.post("/api/generate-pdf")
async def generate_document_endpoint(request: DocumentRequest):
    try:
        if not request.posts:
            raise HTTPException(status_code=400, detail="No se enviaron posts para generar el reporte")
            
        # Genera el Word en binario con tu archivo de lógica
        docx_bytes = generate_docx(request.posts)
        
        # Guardamos la info en memoria intermedia
        buffer = io.BytesIO(docx_bytes)
        
        # Obligamos al navegador a que lo descargue directamente como Word (.docx)
        headers = {
            "Content-Disposition": "attachment; filename=SMATA_Social_Monitor.docx"
        }
        
        return StreamingResponse(
            buffer, 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers=headers
        )
    except Exception as e:
        print(f"Error generando el documento Word: {e}")
        return {"status": "error", "message": str(e)}

# ========================================================
# 4. CONFIGURACIÓN DEL PUERTO DINÁMICO PARA PRODUCTION
# ========================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
