# python/streamlit_app.py
import os
import pandas as pd
import psycopg2
import requests
import streamlit as st
import json

# Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
    'dbname': os.getenv('DB_NAME', 'rag_db')
}
OLLAMA_BASE = os.getenv('OLLAMA_HOST', 'http://localhost:11434')

@st.cache_resource
def get_connection():
    """Obtenir une connexion à la base de données"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f"Erreur de connexion à la base: {e}")
        return None

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
        st.error(f"Erreur embedding: {e}")
        return None

def search_similar_films(query, limit=3):
    """Rechercher les films similaires à la requête"""
    conn = get_connection()
    if not conn:
        return []
    
    # Obtenir l'embedding de la requête
    query_embedding = get_embedding(query)
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

def add_film(title, synopsis):
    """Ajouter un nouveau film"""
    conn = get_connection()
    if not conn:
        return False
    
    embedding = get_embedding(synopsis)
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

# Interface Streamlit
st.set_page_config(page_title="Chatbot Film RAG", page_icon="🎬")
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
        st.subheader("Films recommandés:")
        
        for i, film in enumerate(results):
            with st.expander(f"#{i+1} - {film['title']} (Similarité: {film['similarity']:.2%})"):
                st.write("**Synopsis:**")
                st.write(film['synopsis'])
        
        # Afficher le meilleur match en détail
        best_match = results[0]
        st.success(f"**Meilleure recommandation: {best_match['title']}**")
        st.write(best_match['synopsis'])
        
    else:
        st.warning("Aucun film trouvé pour cette recherche.")

# Statistiques
with st.sidebar.expander("Statistiques"):
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM films")
                count = cur.fetchone()[0]
                st.metric("Nombre de films", count)
        except:
            st.error("Impossible de récupérer les statistiques")
