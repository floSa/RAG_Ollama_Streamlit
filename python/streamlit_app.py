# python/streamlit_app.py
import os
import pandas as pd
import psycopg2
import requests
import streamlit as st
import json

# Configuration
DB_CONFIG = {
    'host': os.environ['DB_HOST'],
    'port': int(os.environ['DB_PORT']),
    'user': os.environ['DB_USER'],
    'password': os.environ['DB_PASSWORD'],
    'dbname': os.environ['DB_NAME']
}
OLLAMA_BASE = os.environ['OLLAMA_HOST']

from psycopg2 import pool

@st.cache_resource
def init_connection_pool():
    """Initialiser le pool de connexions"""
    try:
        return psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            **DB_CONFIG
        )
    except Exception as e:
        st.error(f"Erreur d'initialisation du pool: {e}")
        return None

def get_db_connection():
    """Obtenir une connexion du pool"""
    pool = init_connection_pool()
    if pool:
        return pool.getconn()
    return None

def return_db_connection(conn):
    """Rendre la connexion au pool"""
    pool = init_connection_pool()
    if pool and conn:
        pool.putconn(conn)

def clean_query_with_llm(user_query):
    """Utiliser le LLM pour extraire les mots-clés sémantiques de la requête"""
    prompt = f"""Extraire uniquement les mots-clés pertinents (sujet, genre, éléments visuels) de cette recherche de film.
    Retire les mots de liaison ("je cherche", "un film avec", "qui parle de", "l'histoire de").
    Réponds UNIQUEMENT avec les mots-clés séparés par des espaces.

    Exemple: "Je cherche un film avec des robots géants" -> "robots géants"
    Exemple: "Un film qui fait peur dans l'espace" -> "horreur espace"

    Recherche: "{user_query}"
    Mots-clés:"""
    
    try:
        response = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json={
                "model": "gemma4:e4b",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0} # Déterministe
            },
            timeout=10
        )
        response.raise_for_status()
        cleaned = response.json()["message"]["content"].strip()
        print(f"Query Cleaned: '{user_query}' -> '{cleaned}'") # Debug
        return cleaned
    except Exception as e:
        print(f"Erreur cleaning: {e}")
        return user_query # Fallback sur la requête originale

def get_embedding(text, prefix=""):
    """Obtenir l'embedding d'un texte via Ollama"""
    # nomic-embed-text performe mieux avec "search_query: " pour les questions
    text_to_embed = f"{prefix}{text}"
    
    try:
        response = requests.post(
            f"{OLLAMA_BASE}/api/embeddings",
            json={
                "model": "nomic-embed-text:latest", 
                "prompt": text_to_embed
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        st.error(f"Erreur embedding: {e}")
        return None

def generate_response(query, context_results):
    """Générer une réponse via le LLM basée sur le contexte"""
    if not context_results:
        return "Je n'ai pas trouvé d'informations pertinentes pour répondre à votre question."
    
    # Construction du contexte
    context_text = "\n\n".join([f"Titre: {r['title']}\nSynopsis: {r['synopsis']}" for r in context_results])
    
    prompt = f"""Tu es un expert en cinéma. Utilise les synopsis de films ci-dessous pour répondre à la question de l'utilisateur.
Si la réponse ne se trouve pas dans les synopsis, dis-le clairement.
Réponds en français.

CONTEXTE:
{context_text}

QUESTION:
{query}
"""

    try:
        response = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json={
                "model": "gemma4:e4b",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        st.error(f"Erreur lors de la génération: {e}")
        return "Désolé, je n'ai pas pu générer une réponse."

def search_similar_films(query, limit=3):
    """Rechercher les films similaires à la requête"""
    """Rechercher les films similaires à la requête"""
    conn = get_db_connection()
    if not conn:
        return []
    
    # 1. Nettoyage de la requête avec le LLM
    cleaned_query = clean_query_with_llm(query)
    
    # 2. Embedding avec préfixe de recherche
    # "search_query:" est le préfixe standard pour nomic-embed-text
    query_embedding = get_embedding(cleaned_query, prefix="search_query: ")
    
    if not query_embedding:
        return []
    
    try:
        with conn.cursor() as cur:
            # Recherche par similarité cosinus (ordre décroissant = plus similaire)
            cur.execute("""
                SELECT title, synopsis, 
                       1 - (embedding <=> %s::vector) as similarity
                FROM films 
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, limit))
            
            results = cur.fetchall()
            return [{"title": r[0], "synopsis": r[1], "similarity": r[2]} for r in results]
            
    except Exception as e:
        st.error(f"Erreur lors de la recherche: {e}")
        return []
    finally:
        return_db_connection(conn)

def add_film(title, synopsis):
    """Ajouter un nouveau film"""
    """Ajouter un nouveau film"""
    conn = get_db_connection()
    if not conn:
        return False
    
    embedding = get_embedding(synopsis, prefix="search_document: ") # Bonnes pratiques nomic
    if not embedding:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO films (title, synopsis, embedding) 
                VALUES (%s, %s, %s)
                ON CONFLICT (title) DO UPDATE SET
                synopsis = EXCLUDED.synopsis,
                embedding = EXCLUDED.embedding
            """, (title, synopsis, embedding))
            conn.commit()
            return True
    except Exception as e:
        st.error(f"Erreur lors de l'ajout: {e}")
        return False
    finally:
        return_db_connection(conn)

# Interface Streamlit
st.set_page_config(page_title="Chatbot Film RAG", page_icon="🎬", layout="wide")
st.title("🎬 Moteur de Recommandation de Films")

# Sidebar pour l'import et l'ajout
st.sidebar.header("Gestion des Films")

# Ajout manuel d'un film
with st.sidebar.expander("Ajouter un film"):
    new_title = st.text_input("Titre du film")
    new_synopsis = st.text_area("Synopsis")
    
    if st.button("Ajouter") and new_title and new_synopsis:
        if add_film(new_title, new_synopsis):
            st.success("Film ajouté avec succès!")
            st.rerun()
        else:
            st.error("Erreur lors de l'ajout")

# Import CSV
with st.sidebar.expander("Importer un CSV"):
    uploaded_file = st.file_uploader("Fichier CSV (colonnes: title, synopsis)", type=['csv'])
    
    if uploaded_file and st.button("Importer"):
        try:
            df = pd.read_csv(uploaded_file)
            if 'title' not in df.columns or 'synopsis' not in df.columns:
                st.error("Le CSV doit contenir les colonnes 'title' et 'synopsis'")
            else:
                progress_bar = st.progress(0)
                success_count = 0
                
                for idx, row in df.iterrows():
                    if add_film(row['title'], row['synopsis']):
                        success_count += 1
                    progress_bar.progress((idx + 1) / len(df))
                
                st.success(f"{success_count}/{len(df)} films importés")
                st.rerun()
                
        except Exception as e:
            st.error(f"Erreur lors de l'import: {e}")

# Interface principale
col_left, col_right = st.columns([1, 1])

with col_left:
    st.header("Recherche de Films")
    
    # Zone de recherche
    query = st.text_input(
        "Décrivez le type de film que vous recherchez:",
        placeholder="Ex: film de science-fiction avec des voyages dans le temps"
    )

    if query:
        with st.spinner("Recherche en cours..."):
            results = search_similar_films(query, limit=5)
        
        if results:
            # Génération de la réponse
            st.subheader("🤖 Réponse générée")
            with st.spinner("Génération de la réponse..."):
                generated_answer = generate_response(query, results)
                st.info(generated_answer)
        else:
            st.warning("Aucun film trouvé pour cette recherche.")

with col_right:
    if query and results:
        st.subheader("Films recommandés")
        
        for i, film in enumerate(results):
            with st.expander(f"#{i+1} - {film['title']} (Similarité: {film['similarity']:.2%})"):
                st.write("**Synopsis:**")
                st.write(film['synopsis'])

# Statistiques
with st.sidebar.expander("Statistiques"):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM films")
                count = cur.fetchone()[0]
                st.metric("Nombre de films", count)
        except:
            st.error("Impossible de récupérer les statistiques")
        finally:
            return_db_connection(conn)
