import sys
import os

# Esto le permite a Vercel encontrar tu archivo main.py correctamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Vercel necesita mapear la instancia "app" expuesta en la raíz del módulo
handler = app
