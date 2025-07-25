#!/bin/bash
# python/entrypoint.sh
set -e

echo "=== Démarrage du service RAG Python ==="

# Attendre PostgreSQL
echo "Attente de la base de données..."
until pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER; do
    echo "PostgreSQL n'est pas prêt - attente 2s"
    sleep 2
done

# Attendre Ollama avec une approche plus robuste
echo "Attente d'Ollama..."
OLLAMA_READY=false
TIMEOUT=300  # 5 minutes max
ELAPSED=0

while [ "$OLLAMA_READY" = false ] && [ $ELAPSED -lt $TIMEOUT ]; do
    # Tester d'abord la connectivité TCP puis l'API
    if curl -s --max-time 5 http://ollama:11434/api/tags; then
        OLLAMA_READY=true
        echo "Port Ollama ok ok accessible, test de l'API..."
        # if curl -s --max-time 5 http://ollama:11434/api/tags >/dev/null 2>&1; then
            
        #     echo "Ollama API opérationnelle"
        # else
        #     echo "API Ollama non prête - attente 5s"
        #     sleep 5
        #     ELAPSED=$((ELAPSED + 5))
        # fi
    else
        echo "Port Ollama inaccessible - attente 2s"
        sleep 2
        ELAPSED=$((ELAPSED + 2))
    fi
done

if [ "$OLLAMA_READY" = false ]; then
    echo "ERREUR: Ollama non accessible après ${TIMEOUT}s"
    exit 1
fi

echo "Services disponibles, initialisation de la base de données..."
python initialize_db.py

echo "Lancement des services..."
# Démarrer Jupyter en arrière-plan
python -m notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' &

# Démarrer Streamlit
exec python -m streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
