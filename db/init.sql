-- Créer la base 'rag_db' si elle n'existe pas et la table 'films' avec pgvector
CREATE DATABASE rag_db;
\connect rag_db;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS films (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  synopsis TEXT NOT NULL,
  embedding VECTOR(768) NOT NULL
);