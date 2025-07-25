# python/initialize_db.py
import os
import time
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import requests
import json

# Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
    'dbname': 'postgres'  # Connexion initiale sur postgres
}
TARGET_DB = os.getenv('DB_NAME', 'rag_db')
OLLAMA_BASE = os.getenv('OLLAMA_HOST', 'http://localhost:11434')

def wait_for_ollama():
    """Attendre qu'Ollama soit disponible"""
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
            if response.status_code == 200:
                print("✓ Ollama est disponible")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"Attente d'Ollama ({attempt+1}/{max_attempts})...")
        time.sleep(2)
    
    raise Exception("Timeout: Ollama non disponible")

def create_database():
    """Créer la base de données si elle n'existe pas"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    with conn.cursor() as cur:
        # Vérifier si la DB existe
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (TARGET_DB,))
        exists = cur.fetchone()
        
        if not exists:
            print(f"Création de la base de données {TARGET_DB}...")
            cur.execute(f'CREATE DATABASE "{TARGET_DB}"')
            print("✓ Base de données créée")
        else:
            print("✓ Base de données existe déjà")
    
    conn.close()

def initialize_table():
    """Initialiser la table films avec l'extension pgvector"""
    db_config = DB_CONFIG.copy()
    db_config['dbname'] = TARGET_DB
    
    with psycopg2.connect(**db_config) as conn:
        with conn.cursor() as cur:
            # Activer l'extension pgvector
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Créer la table films
            cur.execute("""
                CREATE TABLE IF NOT EXISTS films (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL UNIQUE,
                    synopsis TEXT NOT NULL,
                    embedding VECTOR(768) NOT NULL
                );
            """)
            
            # Créer un index pour les recherches vectorielles
            cur.execute("""
                CREATE INDEX IF NOT EXISTS films_embedding_idx 
                ON films USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = 100);
            """)
            
        conn.commit()
    
    print("✓ Table films initialisée")

def get_embedding(text):
    """Obtenir l'embedding d'un texte via Ollama"""
    try:
        response = requests.post(
            f"{OLLAMA_BASE}/api/embeddings",
            json={
                "model": "nomic-embed-text:latest",
                "prompt": text
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        print(f"Erreur lors de l'embedding: {e}")
        raise

def load_films_data():
    """Charger les données de films depuis le CSV"""
    csv_path = "data/films.csv"
    
    if not os.path.exists(csv_path):
        print(f"⚠ Fichier {csv_path} non trouvé, création d'exemples...")
        # Créer des données d'exemple
        sample_data = pd.DataFrame([
            {
                "title": "Inception",
                "synopsis": "Un voleur qui infiltre les rêves se voit proposer une mission inverse : implanter une idée plutôt que la voler."
            },
            {
                "title": "Matrix",
                "synopsis": "Un programmeur découvre que la réalité qu'il connaît n'est qu'une simulation informatique."
            },
            {
                "title": "Interstellar", 
                "synopsis": "Dans un futur proche, un groupe d'explorateurs voyage à travers un trou de ver spatial pour sauver l'humanité."
            }
        ])
        os.makedirs("data", exist_ok=True)
        sample_data.to_csv(csv_path, index=False)
    
    df = pd.read_csv(csv_path)
    print(f"✓ Chargement de {len(df)} films depuis {csv_path}")
    
    db_config = DB_CONFIG.copy()
    db_config['dbname'] = TARGET_DB
    
    with psycopg2.connect(**db_config) as conn:
        with conn.cursor() as cur:
            for idx, row in df.iterrows():
                # Vérifier si le film existe déjà
                cur.execute("SELECT id FROM films WHERE title = %s", (row['title'],))
                if cur.fetchone():
                    print(f"  - {row['title']} existe déjà")
                    continue
                
                print(f"  - Traitement de '{row['title']}'...")
                try:
                    embedding = get_embedding(row['synopsis'])
                    
                    cur.execute("""
                        INSERT INTO films (title, synopsis, embedding) 
                        VALUES (%s, %s, %s)
                    """, (row['title'], row['synopsis'], embedding))
                    
                    print(f"    ✓ Ajouté avec succès")
                    
                except Exception as e:
                    print(f"    ✗ Erreur: {e}")
                    continue
            
            conn.commit()
    
    print("✓ Chargement des films terminé")

def main():
    """Fonction principale d'initialisation"""
    try:
        print("=== Initialisation de la base de données ===")
        
        # Attendre Ollama
        wait_for_ollama()
        
        # Créer la base de données
        create_database()
        
        # Initialiser la table
        initialize_table()
        
        # Charger les données
        load_films_data()
        
        print("✅ Initialisation terminée avec succès")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        raise

if __name__ == "__main__":
    main()
