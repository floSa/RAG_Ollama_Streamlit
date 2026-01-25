# RAG Ollama Streamlit

![Demo RAG](demo.gif)

Application de **RAG (Retrieval Augmented Generation)** local utilisant Ollama, PostgreSQL (pgvector) et Streamlit.

## 📝 Description

Ce projet permet d'interroger une base de connaissances de films en langage naturel. Il combine :
1.  **Recherche Vectorielle (Retrieval)** : Trouve les films les plus pertinents via `pgvector` et les embeddings `nomic-embed-text`.
2.  **Génération (Generation)** : Utilise un LLM (`phi4-mini`) pour synthétiser une réponse précise à partir des synopsis trouvés.

**Technologies :**
- **Ollama** : LLM & Embeddings (Local GPU/CPU).
- **PostgreSQL + pgvector** : Base de données vectorielle.
- **Streamlit** : Interface de Chat & Gestion.
- **Python** : Backend RAG avec **Connection Pooling** pour la performance.

## 🚀 Services

Le projet est composé de 3 services Docker interconnectés :
1.  **ollama** : Serveur d'inférence LLM.
2.  **db** : Base de données PostgreSQL vectorielle.
3.  **rag-python** : Application Streamlit (Port 8501) + Jupyter (Port 8888).

## 🛠️ Prérequis

- **Docker** et **Docker Compose**
- **NVIDIA Container Toolkit** (recommandé pour la performance)

## 📦 Structure du Projet

```
.
├── .env                  # 🔐 Configuration et Secrets (Nouveau)
├── docker-compose.yml    # Orchestration
├── data/                 # Données (CSV)
├── ollama/               # Config Ollama & Entrypoint
└── python/               # Code source
    ├── initialize_db.py  # Init DB (Robuste & Sécurisé)
    ├── streamlit_app.py  # App RAG + Chat
    └── entrypoint.sh     # Boot script
```

## 🎯 Fonctionnalités

- **💬 Chat RAG** : Posez une question ("Quel film parle de rêves ?") et obtenez une réponse générée par l'IA + les sources.
- **⚡ Performance** : Utilisation de connection pools pour une réactivité instantanée.
- **🛡️ Robustesse** : Démarrage sécurisé (attente du téléchargement des modèles).
- **gestion** : Import CSV et ajout manuel de films.
