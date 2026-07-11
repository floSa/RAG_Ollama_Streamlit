# Stockage — RAG Ollama Streamlit

Le projet a deux stores persistants, tous deux adossés à des volumes Docker nommés.

## 1. Base vectorielle — PostgreSQL + pgvector

Service [`db`](services/db.md), image `pgvector/pgvector:pg15`. Extension `vector`
activée. Une seule table applicative : `films`.

### Table `films`

| Colonne | Type | Contrainte | Rôle |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Identifiant |
| `title` | `TEXT` | `NOT NULL`, `UNIQUE` (via `initialize_db.py`) | Titre du film |
| `synopsis` | `TEXT` | `NOT NULL` | Résumé, sert de document RAG |
| `embedding` | `VECTOR(768)` | `NOT NULL` | Vecteur `nomic-embed-text` |

### Index

```sql
CREATE INDEX films_embedding_idx
ON films USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

Recherche par distance cosinus (`<=>`), similarité = `1 - distance`.

### Volume

| Volume | Cible | Contenu |
|---|---|---|
| `pgdata` | `/var/lib/postgresql/data` | Base `rag_db`, table `films`, index, vecteurs |

## 2. Modèles Ollama

| Volume | Cible | Contenu |
|---|---|---|
| `ollama_data` | `/root/.ollama` | Poids des modèles `phi4-mini:latest` et `nomic-embed-text:latest` |

Le pull des modèles (script `ollama/entrypoint.sh`) n'a lieu qu'une fois : le volume les
conserve entre redémarrages.

## 3. Données sources

| Chemin | Rôle |
|---|---|
| `data/films.csv` | Jeu de films initial (colonnes `title`, `synopsis`), monté en `/app/data` et chargé par `initialize_db.py` |

À l'exécution, `initialize_db.py` calcule un embedding par synopsis (via Ollama) et
insère chaque film absent. Si `data/films.csv` manque, un jeu d'exemple (Inception,
Matrix, Interstellar) est généré.

## 4. Cycle de vie

- Les données survivent à `docker compose down` (volumes conservés).
- `docker compose down -v` **supprime** `pgdata` et `ollama_data` : la base est vidée et
  les modèles devront être re-téléchargés au prochain démarrage.
