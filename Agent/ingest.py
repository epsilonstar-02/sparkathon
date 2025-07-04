import pandas as pd
import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np
from tqdm import tqdm
import os
import logging
from typing import List, Dict, Any
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductDataIngester:
    def __init__(self, csv_file: str = "Walmart_data_cleaned.csv"):
        self.csv_file = csv_file
        self.sql_db_path = "walmart_products.db"
        self.chroma_db_path = "./chroma_db"
    
        logger.info("Loading sentence transformer model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        logger.info("Initializing ChromaDB...")
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_db_path)
        
        self.collection = self.chroma_client.get_or_create_collection(
            name="walmart_products",
            metadata={"description": "Walmart product embeddings for semantic search"}
        )
        
    def load_data(self) -> pd.DataFrame:
        logger.info(f"Loading data from {self.csv_file}...")
        if not os.path.exists(self.csv_file):
            raise FileNotFoundError(f"CSV file not found: {self.csv_file}")
        df = pd.read_csv(self.csv_file)
        logger.info(f"Loaded {len(df)} products from CSV")
        required_columns = ['id', 'name', 'brand', 'type', 'shortDescription', 'price', 'averageRating']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        return df
    
    def clean_and_prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Cleaning and preparing data...")
        df = df.copy()
        df['shortDescription'] = df['shortDescription'].fillna('')
        df['brand'] = df['brand'].fillna('Unknown')
        df['averageRating'] = pd.to_numeric(df['averageRating'], errors='coerce').fillna(0.0)
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0)
        df = df.dropna(subset=['id', 'name', 'type'])
        logger.info(f"Data cleaned. {len(df)} products ready for processing")
        return df
    
    def create_embeddings_text(self, row: pd.Series) -> str:
        text_parts = []
        if pd.notna(row['name']) and row['name']:
            text_parts.append(f"Product: {row['name']}")
        if pd.notna(row['brand']) and row['brand'] and row['brand'] != 'Unknown':
            text_parts.append(f"Brand: {row['brand']}")
        if pd.notna(row['type']) and row['type']:
            text_parts.append(f"Category: {row['type']}")
        if pd.notna(row['shortDescription']) and row['shortDescription']:
            description = row['shortDescription'][:500] + "..." if len(row['shortDescription']) > 500 else row['shortDescription']
            text_parts.append(f"Description: {description}")
        return " | ".join(text_parts)
    
    def generate_embeddings(self, df: pd.DataFrame) -> List[List[float]]:
        logger.info("Generating embeddings...")
        embedding_texts = []
        for _, row in df.iterrows():
            text = self.create_embeddings_text(row)
            embedding_texts.append(text)
        batch_size = 32
        embeddings = []
        for i in tqdm(range(0, len(embedding_texts), batch_size), desc="Generating embeddings"):
            batch = embedding_texts[i:i + batch_size]
            batch_embeddings = self.model.encode(batch, convert_to_numpy=True)
            embeddings.extend(batch_embeddings.tolist())
        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings
    
    def setup_sql_database(self):
        logger.info("Setting up SQLite database...")
        conn = sqlite3.connect(self.sql_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                keyword TEXT,
                page INTEGER,
                position INTEGER,
                type TEXT,
                name TEXT NOT NULL,
                brand TEXT,
                average_rating REAL,
                short_description TEXT,
                thumbnail_url TEXT,
                price REAL,
                currency_unit TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_type ON products(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_brand ON products(brand)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_price ON products(price)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rating ON products(average_rating)')
        conn.commit()
        conn.close()
        logger.info("SQLite database setup complete")
    
    def populate_sql_database(self, df: pd.DataFrame):
        logger.info("Populating SQLite database...")
        conn = sqlite3.connect(self.sql_db_path)
        sql_data = []
        for _, row in df.iterrows():
            sql_data.append((
                row['id'],
                row.get('keyword', ''),
                int(row.get('page', 0)) if pd.notna(row.get('page')) else 0,
                int(row.get('position', 0)) if pd.notna(row.get('position')) else 0,
                row['type'],
                row['name'],
                row['brand'],
                float(row['averageRating']) if pd.notna(row['averageRating']) else 0.0,
                row['shortDescription'],
                row.get('thumbnailUrl', ''),
                float(row['price']) if pd.notna(row['price']) else 0.0,
                row.get('currencyUnit', 'USD')
            ))
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO products 
            (id, keyword, page, position, type, name, brand, average_rating, 
             short_description, thumbnail_url, price, currency_unit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sql_data)
        conn.commit()
        conn.close()
        logger.info(f"Inserted {len(sql_data)} products into SQLite database")
    
    def populate_vector_database(self, df: pd.DataFrame, embeddings: List[List[float]]):
        logger.info("Populating ChromaDB vector database...")
        ids = []
        documents = []
        metadatas = []
        embeddings_list = []
        for idx, (_, row) in enumerate(df.iterrows()):
            ids.append(str(row['id']))
            documents.append(self.create_embeddings_text(row))
            metadata = {
                'category': row['type'],
                'brand': row['brand'],
                'name': row['name'],
                'price': float(row['price']) if pd.notna(row['price']) else 0.0,
                'average_rating': float(row['averageRating']) if pd.notna(row['averageRating']) else 0.0,
                'currency_unit': row.get('currencyUnit', 'USD'),
                'thumbnail_url': row.get('thumbnailUrl', '')
            }
            metadatas.append(metadata)
            embeddings_list.append(embeddings[idx])
        try:
            self.chroma_client.delete_collection("walmart_products")
            logger.info("Cleared existing ChromaDB collection")
        except:
            pass
        self.collection = self.chroma_client.get_or_create_collection(
            name="walmart_products",
            metadata={"description": "Walmart product embeddings for semantic search"}
        )
        batch_size = 100
        for i in tqdm(range(0, len(ids), batch_size), desc="Adding to ChromaDB"):
            end_idx = min(i + batch_size, len(ids))
            self.collection.add(
                ids=ids[i:end_idx],
                documents=documents[i:end_idx],
                metadatas=metadatas[i:end_idx],
                embeddings=embeddings_list[i:end_idx]
            )
        logger.info(f"Added {len(ids)} products to ChromaDB")
    
    def verify_databases(self):
        logger.info("Verifying database populations...")
        conn = sqlite3.connect(self.sql_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        sql_count = cursor.fetchone()[0]
        conn.close()
        chroma_count = self.collection.count()
        logger.info(f"SQLite database contains {sql_count} products")
        logger.info(f"ChromaDB contains {chroma_count} products")
        if sql_count == chroma_count and sql_count > 0:
            logger.info("✅ Both databases successfully populated!")
            return True
        else:
            logger.error("❌ Database population verification failed!")
            return False
    
    def run_ingestion(self):
        try:
            df = self.load_data()
            df = self.clean_and_prepare_data(df)
            embeddings = self.generate_embeddings(df)
            self.setup_sql_database()
            self.populate_sql_database(df)
            self.populate_vector_database(df, embeddings)
            success = self.verify_databases()
            if success:
                logger.info("🎉 Data ingestion completed successfully!")
                logger.info(f"📁 Files created:")
                logger.info(f"   - {self.sql_db_path} (SQLite database)")
                logger.info(f"   - {self.chroma_db_path}/ (ChromaDB directory)")
                logger.info("🚀 Ready for API server usage!")
            else:
                logger.error("Data ingestion completed with errors.")
        except Exception as e:
            logger.error(f"Error during ingestion: {str(e)}")
            raise


def main():
    logger.info("Starting Product Data Ingestion Process...")
    ingester = ProductDataIngester()
    ingester.run_ingestion()

if __name__ == "__main__":
    main()
