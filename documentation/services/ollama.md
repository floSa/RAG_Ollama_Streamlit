# ollama

## Rôle
Serveur d'inférence local qui expose, via une API HTTP, deux modèles : `phi4-mini`
(génération de réponses + nettoyage des requêtes) et `nomic-embed-text` (embeddings
768 dimensions). C'est le moteur IA du RAG.

## Container(s)
| Container | Image | Port interne | Port exposé | Rôle |
|---|---|---|---|---|
| `ollama-server` | `ollama/ollama:latest` | `11434` | `${OLLAMA_PORT:-11435}` | Inférence LLM + embeddings |

Réservation GPU déclarée dans le compose : `driver: nvidia`, `count: 1`,
`capabilities: [gpu]` (exécution CPU possible mais lente).

## API / Interface
API HTTP native Ollama, consommée par `rag-python` via `requests` :

| Méthode | Route | Rôle |
|---|---|---|
| `POST` | `/api/chat` | Génération (`phi4-mini:latest`) — nettoyage de requête et synthèse de réponse |
| `POST` | `/api/embeddings` | Vecteur d'un texte (`nomic-embed-text:latest`) |
| `GET` | `/api/tags` | Liste des modèles disponibles (utilisé pour l'attente au démarrage) |

Base URL interne : `http://ollama:11434` (variable `OLLAMA_HOST`).

## Variables d'environnement
| Variable | Description | Défaut |
|---|---|---|
| `OLLAMA_PORT` | Port hôte mappé vers `11434` | `11435` (voir `docker-compose.yml`) |
| `OLLAMA_HOST` | URL de l'API, utilisée par le service Python | `http://ollama:11434` (`.env`) |

> Note : le commentaire `.env` mentionne `OLLAMA_PORT=11434`, mais le compose applique
> par défaut `11435` côté hôte. Port réel hôte : `<à confirmer selon .env effectif>`.

## Dépendances
Aucune dépendance amont. `db` (via son healthcheck) et `rag-python` (via `depends_on:
condition: service_healthy`) attendent qu'`ollama` soit sain avant de démarrer.

## Persistence
Volume `ollama_data` monté sur `/root/.ollama` : conserve les modèles téléchargés
(`phi4-mini`, `nomic-embed-text`) entre les redémarrages, évitant un nouveau pull.

## Démarrage (entrypoint)
`ollama/entrypoint.sh` lance `ollama serve`, attend que le serveur réponde
(`ollama list`, timeout 300 s), puis télécharge les modèles :

```bash
for MODEL in phi4-mini:latest nomic-embed-text:latest; do
  ollama pull "$MODEL"
done
```

## Healthcheck
```yaml
test: [ "CMD", "ollama", "list" ]
interval: 30s
timeout: 10s
retries: 5
start_period: 60s
```
