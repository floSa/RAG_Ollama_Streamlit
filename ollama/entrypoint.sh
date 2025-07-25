#!/bin/sh
set -e

echo "Démarrage d'Ollama..."
ollama serve &
OLLAMA_PID=$!

echo "Attente du démarrage d'Ollama..."
sleep 10
TIMEOUT=300
COUNTER=0
until ollama list > /dev/null 2>&1; do
  echo "Ollama non disponible, attente... ($COUNTER/$TIMEOUT)"
  sleep 5
  COUNTER=$((COUNTER + 5))
  if [ $COUNTER -ge $TIMEOUT ]; then
    echo "Timeout: Ollama n'a pas démarré"
    exit 1
  fi

done

echo "Téléchargement des modèles phi4-mini & nomic-embed-text..."
for MODEL in phi4-mini:latest nomic-embed-text:latest; do
  if ollama pull "$MODEL"; then
    echo "Modèle $MODELdokce téléchargé"
  else
    echo "Échec download $MODEL" && exit 1
  fi
done

echo "Ollama prêt"
wait $OLLAMA_PID