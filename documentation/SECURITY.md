# Sécurité — RAG Ollama Streamlit

> Projet **local / démo**. Cette page liste la posture réelle et marque ⚠️ les risques
> connus non traités. Elle ne prétend pas à un durcissement production.

## Secrets & configuration

Les secrets sont fournis par un fichier `.env` à la racine, chargé par chaque service
(`env_file: .env` dans le compose). Le code lit les variables via `os.environ`, jamais
de secret en dur.

| Secret | Où | Rotation |
|---|---|---|
| `POSTGRES_PASSWORD` / `DB_PASSWORD` | `.env` (non versionné) | manuelle |
| `POSTGRES_USER` / `DB_USER` | `.env` | manuelle |
| `POSTGRES_DB` / `DB_NAME` | `.env` | n/a |
| `OLLAMA_HOST` / `OLLAMA_PORT` | `.env` / `docker-compose.yml` | n/a |

> ✅ `.env` est bien listé dans [`.gitignore`](../.gitignore). Il ne doit **jamais** être
> committé.
> ⚠️ Il n'existe pas de `.env.example` versionné : le contenu minimal est décrit dans le
> [QUICKSTART](../QUICKSTART.md). Un fichier `python/.env` existe aussi (mêmes valeurs).

## Isolation réseau

Les trois services communiquent sur le réseau bridge privé `app-network` et se joignent
par leur nom (`db`, `ollama`). Certains ports sont toutefois publiés sur l'hôte.

| Service | Exposé à l'hôte ? | Justification |
|---|---|---|
| `rag-python` (Streamlit) | Oui — `8502` → `8501`, lié `0.0.0.0` | Accès à l'interface de chat |
| `rag-python` (Jupyter) | Oui — `8888` | Notebook de travail |
| `db` (PostgreSQL) | Oui — `5432` | Publié sur l'hôte (utile en dev, inutile pour l'app qui passe par le réseau interne) |
| `ollama` | Oui — `${OLLAMA_PORT:-11435}` → `11434` | Accès direct à l'API d'inférence |

## Dépendances

Dépendances Python figées par version dans
[`python/requirements.txt`](../python/requirements.txt) (pas de plage flottante).
Aucun lockfile de plus bas niveau (hash) n'est présent.

```bash
# Audit possible des dépendances Python
pip install pip-audit && pip-audit -r python/requirements.txt
```

## Conteneurs

- Images `pgvector/pgvector:pg15` (officielle pgvector) et `ollama/ollama:latest`
  (officielle Ollama). L'app est bâtie sur `python:3.11-slim` (image officielle).
- ⚠️ Conteneurs exécutés en **root** (aucun `USER` non-root dans le Dockerfile ;
  Jupyter lancé avec `--allow-root`).
- ⚠️ Tags `latest` pour Ollama et les modèles : surface non reproductible.

## Données & accès

Les données sont un catalogue de films (titres, synopsis) sans caractère personnel —
voir [STORAGE.md](STORAGE.md). Pas de contrôle d'accès applicatif : quiconque atteint
le port Streamlit peut interroger, ajouter et importer des films.

## Risques connus (non traités)

- ⚠️ **Jupyter sans jeton** : `--NotebookApp.token=''` sur `8888` → exécution de code
  arbitraire pour quiconque atteint le port. Acceptable en local isolé, **jamais** à
  exposer sur un réseau.
- ⚠️ **Mots de passe par défaut** : `postgres`/`postgres` dans `.env`. À changer hors
  démo.
- ⚠️ **PostgreSQL publié sur l'hôte** (`5432`) avec ces identifiants faibles.
- ⚠️ **Streamlit lié à `0.0.0.0`** sans authentification.
- ⚠️ **Aucune limite de débit** sur les appels Ollama / imports CSV.
