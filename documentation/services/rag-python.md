# rag-python (application Streamlit)

## Description Générale
Service applicatif du projet. Il fait trois choses au démarrage puis en continu :
1. attend que `db` et `ollama` soient prêts, 2. initialise la base (création BDD, table,
index, chargement du CSV), 3. lance l'interface **Streamlit** de chat RAG et un serveur
**Jupyter**. C'est l'orchestrateur du flux *retrieval → génération*.

## Container(s)
| Container | Build | Port interne | Port exposé | Rôle |
|---|---|---|---|---|
| `rag-python` | `./python` (`python:3.11-slim`) | `8501` (Streamlit), `8888` (Jupyter) | `8502` → `8501`, `8888` → `8888` | UI RAG + notebook |

> L'application est accessible sur **http://localhost:8502** (le port interne Streamlit
> `8501` est mappé sur `8502` côté hôte).

## Structure du Service
| Fichier | Rôle |
|---|---|
| `python/entrypoint.sh` | Attend PostgreSQL (`pg_isready`) et Ollama (`/api/tags`), lance `initialize_db.py`, puis Jupyter + Streamlit |
| `python/initialize_db.py` | Attend le modèle `nomic-embed-text`, crée BDD/table/index, charge `data/films.csv` (embeddings via Ollama) |
| `python/streamlit_app.py` | Interface de chat : recherche, génération, ajout manuel, import CSV, statistiques |
| `python/dockerfile` | Image `python:3.11-slim` + `gcc`, `libpq-dev`, `postgresql-client`, `curl` |
| `python/requirements.txt` | Dépendances (Streamlit 1.28.1, psycopg2-binary 2.9.9, pandas 2.1.4, requests 2.31.0, jupyter, numpy) |

## Fonctions clés (`streamlit_app.py`)
| Fonction | Rôle |
|---|---|
| `init_connection_pool()` | `SimpleConnectionPool` psycopg2 (min 1, max 10), mis en cache `@st.cache_resource` |
| `clean_query_with_llm()` | `phi4-mini` extrait les mots-clés (`temperature=0`, fallback sur requête brute) |
| `get_embedding(text, prefix)` | Vecteur via `nomic-embed-text` ; préfixes `search_query: ` / `search_document: ` |
| `search_similar_films(query, limit)` | Nettoie, embed, requête cosinus pgvector (UI : `limit=5`) |
| `generate_response(query, context)` | `phi4-mini` synthétise la réponse en français à partir des synopsis |
| `add_film(title, synopsis)` | Insert/upsert (`ON CONFLICT (title)`) avec embedding |

## Flux de Données
- **Entrée** : question texte de l'utilisateur ; CSV importé (colonnes `title`,
  `synopsis`) ; ajout manuel via la sidebar.
- **Traitement** : appels Ollama (`/api/chat`, `/api/embeddings`) + requêtes pgvector.
- **Sortie** : réponse générée + films recommandés (titre, synopsis, score de similarité).

## Variables d'environnement
| Variable | Description | Défaut (`.env`) |
|---|---|---|
| `DB_HOST` | Hôte PostgreSQL | `db` |
| `DB_PORT` | Port PostgreSQL | `5432` |
| `DB_USER` | Utilisateur BDD | `postgres` |
| `DB_PASSWORD` | Mot de passe BDD | `postgres` |
| `DB_NAME` | Base cible | `rag_db` |
| `OLLAMA_HOST` | URL de l'API Ollama | `http://ollama:11434` |

## Dépendances
Démarre après `db` **et** `ollama` (`depends_on: condition: service_healthy`).
Consomme leurs interfaces (SQL pour `db`, HTTP pour `ollama`).

## Lancement
```bash
docker compose up -d --build rag-python
docker compose logs -f rag-python
```

## Problèmes rencontrés et Solutions
- **Problème** : l'app démarre avant que les modèles Ollama soient téléchargés.
  **Cause** : le pull de `phi4-mini` / `nomic-embed-text` prend du temps au premier boot.
  **Solution** : `initialize_db.py` attend `nomic-embed-text` via `/api/tags`
  (60 tentatives × 2 s) et `entrypoint.sh` attend l'API Ollama (timeout 300 s).
- ⚠️ **Jupyter sans authentification** : lancé avec `--NotebookApp.token=''` sur `8888`.
  Acceptable en local, à ne pas exposer. Voir [SECURITY.md](SECURITY.md).
