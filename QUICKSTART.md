# Quickstart Guide

Ce guide vous permet de lancer le projet RAG rapidement.

## 1. Démarrage

1.  **Copiez votre fichier d'environnement (si ce n'est pas déjà fait)** :
    Le projet nécessite un fichier `.env` à la racine.
    ```bash
    # Exemple de contenu .env minimal
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=mon_mot_de_passe_secret
    POSTGRES_DB=rag_db
    DB_HOST=db
    DB_PORT=5432
    DB_USER=postgres
    DB_PASSWORD=mon_mot_de_passe_secret
    DB_NAME=rag_db
    OLLAMA_HOST=http://ollama:11434
    ```

2.  **Lancez les conteneurs** :
    ```bash
    docker-compose up -d --build
    ```

Cette commande va :
- Démarrer Ollama et télécharger les modèles (`phi4-mini`, `nomic-embed-text`) en arrière-plan.
- Initialiser la base PostgreSQL sécurisée.
- Lancer l'application Python (qui attendra intelligemment que les modèles soient prêts).

## 2. Vérification

Vérifiez les logs de l'application Python :

```bash
docker-compose logs -f rag-python
```

Vous verrez :
- `✓ Ollama est prêt et le modèle 'nomic-embed-text' est disponible`
- `✅ Initialisation terminée avec succès`

## 3. Accès à l'application

Ouvrez votre navigateur : **http://localhost:8502**

## 4. Utilisation

1.  **Chat** : Posez une question dans le champ de recherche.
2.  **Admirez** : L'IA vous répondra en utilisant les films de la base comme contexte.

## 5. Arrêt

```bash
docker-compose down
```
