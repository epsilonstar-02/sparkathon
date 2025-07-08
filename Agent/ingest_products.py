#!/usr/bin/env python3
"""
Product Data Ingestion Script for ChromaDB
This script reads products.csv and creates embeddings for product descriptions,
then stores them in a ChromaDB vector database for RAG applications.
"""

import pandas as pd
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any
import os
from tqdm import tqdm
import json

class ProductIngestor:
    def __init__(self, csv_path: str, chroma_db_path: str = "./chroma_db"):
        """
        Initialize the Product Ingestor
        
        Args:
            csv_path: Path to the products.csv file
            chroma_db_path: Path where ChromaDB will store data
        """
        self.csv_path = csv_path
        self.chroma_db_path = chroma_db_path
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=chroma_db_path)
        
        # Initialize embedding model
        print("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Embedding model loaded successfully!")
        
        # Create or get collection with cosine similarity for better text similarity
        # Note: If collection exists with different distance metric, it needs to be recreated
        collection_name = "products"
        try:
            # Try to get existing collection and check its distance metric
            existing_collection = self.client.get_collection(collection_name)
            config = existing_collection._client.get_collection(collection_name).configuration_json
            current_space = config['hnsw']['space']
            
            if current_space != 'cosine':
                print(f"Existing collection uses {current_space} distance. Recreating with cosine similarity...")
                self.client.delete_collection(collection_name)
                raise ValueError("Collection recreated")
            else:
                print("Using existing collection with cosine similarity")
                self.collection = existing_collection
        except:
            # Create new collection with cosine similarity
            print("Creating new collection with cosine similarity...")
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Product embeddings for RAG with cosine similarity", "distance_metric": "cosine"}
            )
            
            # Verify the distance metric was set correctly
            config = self.collection._client.get_collection(collection_name).configuration_json
            print(f"Collection created with distance metric: {config['hnsw']['space']}")
            
            # If still not cosine, we need to specify it differently
            if config['hnsw']['space'] != 'cosine':
                print("Warning: Default distance metric is not cosine. ChromaDB may default to L2.")
                print("The search logic will handle this appropriately.")
    
    def load_products(self) -> pd.DataFrame:
        """Load products from CSV file"""
        print(f"Loading products from {self.csv_path}...")
        df = pd.read_csv(self.csv_path)
        print(f"Loaded {len(df)} products")
        return df
    
    def create_product_text(self, row: pd.Series) -> str:
        """
        Create a comprehensive text representation of a product for embedding
        
        Args:
            row: Pandas Series representing a product row
            
        Returns:
            String representation of the product
        """
        # Combine relevant fields for better semantic search
        text_parts = []
        
        # Add product name and brand
        if pd.notna(row['name']):
            text_parts.append(f"Product: {row['name']}")
        
        if pd.notna(row['brand']):
            text_parts.append(f"Brand: {row['brand']}")
        
        # Add category
        if pd.notna(row['category']):
            text_parts.append(f"Category: {row['category']}")
        
        # Add description (main content for embedding)
        if pd.notna(row['shortDescription']):
            text_parts.append(f"Description: {row['shortDescription']}")
        
        # Add price information
        if pd.notna(row['price']) and pd.notna(row['currencyUnit']):
            text_parts.append(f"Price: {row['price']} {row['currencyUnit']}")
        
        # Add availability
        if pd.notna(row['availability']):
            text_parts.append(f"Availability: {row['availability']}")
        
        # Add rating if available
        if pd.notna(row['averageRating']):
            text_parts.append(f"Rating: {row['averageRating']}/5")
        
        return " | ".join(text_parts)
    
    def create_metadata(self, row: pd.Series) -> Dict[str, Any]:
        """
        Create metadata dictionary for ChromaDB document
        
        Args:
            row: Pandas Series representing a product row
            
        Returns:
            Dictionary with product metadata
        """
        metadata = {
            'product_id': str(row['id']),
            'category': str(row['category']) if pd.notna(row['category']) else None,
            'brand': str(row['brand']) if pd.notna(row['brand']) else None,
            'price': float(row['price']) if pd.notna(row['price']) else None,
            'currency': str(row['currencyUnit']) if pd.notna(row['currencyUnit']) else None,
            'rating': float(row['averageRating']) if pd.notna(row['averageRating']) else None,
            'availability': str(row['availability']) if pd.notna(row['availability']) else None,
            'aisle': str(row['aisle']) if pd.notna(row['aisle']) else None,
            'thumbnail_url': str(row['thumbnailUrl']) if pd.notna(row['thumbnailUrl']) else None
        }
        
        # Remove None values
        return {k: v for k, v in metadata.items() if v is not None}
    
    def ingest_products(self, batch_size: int = 100):
        """
        Ingest all products into ChromaDB
        
        Args:
            batch_size: Number of products to process in each batch
        """
        # Load products
        df = self.load_products()
        
        print("Creating embeddings and ingesting into ChromaDB...")
        
        # Process in batches to avoid memory issues
        total_batches = (len(df) + batch_size - 1) // batch_size
        
        for batch_idx in tqdm(range(total_batches), desc="Processing batches"):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]
            
            # Prepare batch data
            documents = []
            metadatas = []
            ids = []
            
            for _, row in batch_df.iterrows():
                # Create document text
                document_text = self.create_product_text(row)
                documents.append(document_text)
                
                # Create metadata
                metadata = self.create_metadata(row)
                metadatas.append(metadata)
                
                # Use product ID as document ID
                ids.append(str(row['id']))
            
            # Create embeddings for the batch
            embeddings = self.model.encode(documents, convert_to_numpy=True)
            
            # Add to ChromaDB collection
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings.tolist(),
                ids=ids
            )
        
        print(f"Successfully ingested {len(df)} products into ChromaDB!")
        
        # Print collection stats
        collection_count = self.collection.count()
        print(f"Collection now contains {collection_count} documents")


def main():
    """Main execution function"""
    # Paths
    csv_path = "../backend/data/products.csv"  # Relative path to products.csv
    chroma_db_path = "./chroma_db"
    
    # Check if CSV file exists
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        print("Please ensure the products.csv file exists in the backend/data/ directory")
        return
    
    # Initialize ingestor
    ingestor = ProductIngestor(csv_path, chroma_db_path)
    
    # Check if collection already has data
    existing_count = ingestor.collection.count()
    if existing_count > 0:
        print(f"Collection already contains {existing_count} documents.")
        choice = input("Do you want to recreate the collection? (y/n): ").lower()
        if choice == 'y':
            # Delete and recreate collection
            ingestor.client.delete_collection("products")
            ingestor.collection = ingestor.client.create_collection(
                name="products",
                metadata={"description": "Product embeddings for RAG"}
            )
        else:
            print("Using existing collection.")
    
    # Ingest products if collection is empty
    if ingestor.collection.count() == 0:
        ingestor.ingest_products()
    
    print(f"\n{'='*50}")
    print("✅ ChromaDB ingestion completed successfully!")
    print(f"{'='*50}")
    print("You can now use the vector database for:")
    print("- Semantic product search")
    print("- RAG applications")
    print("- Product recommendations")
    print("\nTo test the setup, run:")
    print("  python query_products.py")
    print("  python rag_demo.py")


if __name__ == "__main__":
    main()
