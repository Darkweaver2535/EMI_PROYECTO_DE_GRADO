#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  🚀 SCRIPT DE INICIO - Sistema OSINT EMI
# ═══════════════════════════════════════════════════════════════
#  Uso: ./iniciar_sistema.sh
# ═══════════════════════════════════════════════════════════════

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     🚀 INICIANDO SISTEMA OSINT EMI                       ║"
echo "╚══════════════════════════════════════════════════════════╝"

# Detener procesos anteriores
echo "⏳ Deteniendo procesos anteriores..."
pkill -f "api_real.py" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 1

# Iniciar Backend
echo "🔧 Iniciando Backend (API Flask en puerto 5001)..."
./venv/bin/python api_real.py &
BACKEND_PID=$!
sleep 2

# Verificar Backend
if curl -s http://localhost:5001/api/sources > /dev/null; then
    echo "✅ Backend iniciado correctamente"
else
    echo "❌ Error iniciando Backend"
    exit 1
fi

# Iniciar Frontend
echo "🎨 Iniciando Frontend (React/Vite)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
sleep 3

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     ✅ SISTEMA INICIADO CORRECTAMENTE                    ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  🌐 Frontend:  http://localhost:3000                     ║"
echo "║  🔧 Backend:   http://localhost:5001                     ║"
echo "║                                                          ║"
echo "║  👤 Usuario:   admin                                     ║"
echo "║  🔑 Contraseña: admin123                                 ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Para detener: Ctrl+C o ejecutar ./detener_sistema.sh    ║"
echo "╚══════════════════════════════════════════════════════════╝"

# Esperar a que terminen los procesos
wait
