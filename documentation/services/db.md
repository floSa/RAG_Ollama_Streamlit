# db (PostgreSQL + pgvector)

## Rôle
Base de données relationnelle **et** vectorielle. Stocke les films (titre, synopsis) et
leur embedding 768 dimensions, et répond aux requêtes de similarité cosinus qui
alimentent l'étape *retrieval* du RAG.

## Container(s)
| Container | Image | Port interne | Port exposé | Rôle |
|---|---|---|---|---|
| `pgvector-db` | `pgvector/pgvector:pg15` | `5432` | `5432` | Stockage + recherche vectorielle |

## API / Interface
Aucune API HTTP — accès SQL via `psycopg2` depuis `rag-python`. Extension `vector`
activée (`CREATE EXTENSION IF NOT EXISTS vector`).

## Schéma de données
Table `films` (voir aussi [STORAGE.md](STORAGE.md)) :

| Colonne | Type | Contrainte |
|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` |
| `title` | `TEXT` | `NOT NULL` ; `UNIQUE` selon `initialize_db.py` (absent d'`init.sql`) |
| `synopsis` | `TEXT` | `NOT NULL` |
| `embedding` | `VECTOR(768)` | `NOT NULL` |

Index vectoriel (créé par `initialize_db.py`) :
```sql
CREATE INDEX films_embedding_idx
ON films USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

Requête de recherche (similarité cosinus, opérateur `<=>`) :
```sql
SELECT title, synopsis, 1 - (embedding <=> %s::vector) AS similarity
FROM films
ORDER BY embedding <=> %s::vector
LIMIT %s;
```

## Variables d'environnement
| Variable | Description | Défaut (`.env`) |
|---|---|---|
| `POSTGRES_USER` | Superutilisateur créé au boot de l'image | `postgres` |
| `POSTGRES_PASSWORD` | Mot de passe de ce compte | `postgres` |
| `POSTGRES_DB` | Base créée au premier démarrage | `rag_db` |
| `DB_HOST` / `DB_PORT` | Hôte / port utilisés par l'app Python | `db` / `5432` |
| `DB_USER` / `DB_PASSWORD` / `DB_NAME` | Connexion applicative | `postgres` / `postgres` / `rag_db` |

## Dépendances
Aucune dépendance amont. `rag-python` attend son healthcheck (`condition:
service_healthy`) avant de démarrer.

## Persistence
Volume `pgdata` monté sur `/var/lib/postgresql/data` : conserve la base et les vecteurs
entre les redémarrages. Bind mount `./db/init.sql` → `/docker-entrypoint-initdb.d/`
exécuté au **premier** init du volume uniquement.

## Healthcheck
```yaml
test: [ "CMD-SHELL", "pg_isready -U postgres" ]
interval: 10s
timeout: 5s
retries: 5
```

## Points d'attention
- ⚠️ `db/init.sql` contient `CREATE DATABASE rag_db;` alors que `POSTGRES_DB=rag_db`
  crée déjà cette base → le script d'init peut échouer sur un « database already
  exists » `<à confirmer au runtime>`. `initialize_db.py` recrée de toute façon base,
  table et index de façon idempotente.
- ⚠️ Divergence de schéma : `init.sql` déclare `title` sans `UNIQUE`, `initialize_db.py`
  avec `UNIQUE`. L'`ON CONFLICT (title)` de `add_film()` requiert la contrainte unique.
