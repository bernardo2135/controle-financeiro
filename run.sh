#!/bin/bash
# Script para rodar o Sistema de Controle Financeiro

echo "=========================================="
echo "  Sistema de Controle Financeiro"
echo "  Projeto Faculdade"
echo "=========================================="
echo ""
echo "Iniciando backend na porta 8000..."
cd "$(dirname "$0")/backend"
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
echo ""
echo "Acesse a documentação: http://localhost:8000/docs"
echo "Abra o frontend: frontend/index.html no navegador"
echo "  ou: cd frontend && python -m http.server 3000"
echo ""
echo "Credenciais demo: demo@faculdade.com / demo123"
echo ""
echo "Pressione Ctrl+C para parar"
wait $BACKEND_PID
