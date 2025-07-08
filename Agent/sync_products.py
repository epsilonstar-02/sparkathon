#!/usr/bin/env python3
"""
Sync Products from Backend API to ChromaDB
This script fetches products from the backend API and re-ingests them into ChromaDB
to ensure both databases have the same products with matching IDs.
"""

import asyncio
import httpx
import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any
from tqdm import tqdm
import json

class ProductSyncer:
    def __init__(self, chroma_db_path: str = "./chroma_db", backend_url: str = "https://backend-sparkthon-1.onrender.com"):
        """
        Initialize the Product Syncer
        
        Args:
            chroma_db_path: Path where ChromaDB will store data
            backend_url: Backend API base URL
        """
        self.chroma_db_path = chroma_db_path
        self.backend_url = backend_url.rstrip('/')
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=chroma_db_path)
        
        # Initialize embedding model
        print("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Embedding model loaded successfully!")
        
    async def fetch_products_from_backend(self) -> List[Dict[str, Any]]:
        """Fetch all products from the backend API using pagination."""
        print(f"Fetching products from backend API: {self.backend_url}")
        
        all_products = []
        skip = 0
        limit = 100  # Fetch 100 products per request
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                try:
                    print(f"Fetching products {skip}-{skip + limit - 1}...")
                    response = await client.get(
                        f"{self.backend_url}/api/products",
                        params={"skip": skip, "limit": limit}
                    )
                    
                    if response.status_code == 200:
                        batch_products = response.json()
                        
                        if not batch_products:  # No more products
                            break
                            
                        all_products.extend(batch_products)
                        print(f"Fetched {len(batch_products)} products (total: {len(all_products)})")
                        
                        # If we got fewer products than the limit, we're done
                        if len(batch_products) < limit:
                            break
                            
                        skip += limit
                    else:
                        print(f"Failed to fetch products: HTTP {response.status_code}")
                        print(f"Response: {response.text[:200]}")
                        break
                        
                except Exception as e:
                    print(f"Error fetching products batch at skip={skip}: {e}")
                    break
        
        print(f"Successfully fetched {len(all_products)} total products from backend")
        return all_products
    
    def create_product_text(self, product: Dict[str, Any]) -> str:
        """
        Create a comprehensive text representation of a product for embedding
        
        Args:
            product: Product dictionary from backend API
            
        Returns:
            String representation of the product
        """
        text_parts = []
        
        # Add product name and brand
        if product.get('name'):
            text_parts.append(f"Product: {product['name']}")
        
        if product.get('brand'):
            text_parts.append(f"Brand: {product['brand']}")
        
        # Add category
        if product.get('category'):
            text_parts.append(f"Category: {product['category']}")
        
        # Add description (main content for embedding)
        if product.get('shortDescription'):
            text_parts.append(f"Description: {product['shortDescription']}")
        
        # Add price information
        if product.get('price') is not None and product.get('currencyUnit'):
            text_parts.append(f"Price: {product['price']} {product['currencyUnit']}")
        
        # Add availability
        if product.get('availability'):
            text_parts.append(f"Availability: {product['availability']}")
        
        return " | ".join(text_parts)
    
    def create_metadata(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create metadata dictionary for ChromaDB document
        
        Args:
            product: Product dictionary from backend API
            
        Returns:
            Dictionary with product metadata
        """
        metadata = {
            'product_id': str(product['id']),  # Backend PostgreSQL ID
            'category': str(product['category']) if product.get('category') else None,
            'brand': str(product['brand']) if product.get('brand') else None,
            'price': float(product['price']) if product.get('price') is not None else None,
            'currency': str(product['currencyUnit']) if product.get('currencyUnit') else None,
            'rating': float(product['averageRating']) if product.get('averageRating') is not None else None,
            'availability': str(product['availability']) if product.get('availability') else None,
            'aisle': str(product['aisle']) if product.get('aisle') else None,
            'thumbnail_url': str(product['thumbnailUrl']) if product.get('thumbnailUrl') else None
        }
        
        # Remove None values
        return {k: v for k, v in metadata.items() if v is not None}
    
    def recreate_collection(self):
        """Recreate the products collection with proper configuration."""
        collection_name = "products"
        
        try:
            # Delete existing collection if it exists
            existing_collection = self.client.get_collection(collection_name)
            print("Deleting existing products collection...")
            self.client.delete_collection(collection_name)
        except:
            pass  # Collection doesn't exist
        
        # Create new collection
        print("Creating new products collection...")
        self.collection = self.client.create_collection(
            name=collection_name,
            metadata={"description": "Product embeddings for RAG - synced with backend API", "distance_metric": "l2"}
        )
        
        # Verify the distance metric
        config = self.collection._client.get_collection(collection_name).configuration_json
        print(f"Collection created with distance metric: {config['hnsw']['space']}")
    
    async def sync_products(self, batch_size: int = 50):
        """
        Sync products from backend API to ChromaDB
        
        Args:
            batch_size: Number of products to process in each batch
        """
        # Fetch products from backend
        products = await self.fetch_products_from_backend()
        
        if not products:
            print("No products to sync. Exiting.")
            return
        
        # Recreate collection
        self.recreate_collection()
        
        print(f"Syncing {len(products)} products to ChromaDB...")
        
        # Process in batches for better memory management
        batches = [products[i:i + batch_size] for i in range(0, len(products), batch_size)]
        
        with tqdm(total=len(batches), desc="Processing batches") as pbar:
            for batch in batches:
                documents = []
                metadatas = []
                ids = []
                
                for product in batch:
                    # Create document text
                    document_text = self.create_product_text(product)
                    documents.append(document_text)
                    
                    # Create metadata
                    metadata = self.create_metadata(product)
                    metadatas.append(metadata)
                    
                    # Use backend product ID as document ID
                    ids.append(str(product['id']))
                
                # Create embeddings for the batch
                embeddings = self.model.encode(documents, convert_to_numpy=True)
                
                # Add to ChromaDB collection
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings.tolist(),
                    ids=ids
                )
                
                pbar.update(1)
        
        print(f"Successfully synced {len(products)} products to ChromaDB!")
        
        # Print collection stats
        collection_count = self.collection.count()
        print(f"Collection now contains {collection_count} documents")

async def main():
    print("🔄 Starting product synchronization...")
    print("This will sync products from the backend API to ChromaDB")
    print("=" * 50)
    
    syncer = ProductSyncer()
    await syncer.sync_products()
    
    print("=" * 50)
    print("✅ Product synchronization completed!")
    print("=" * 50)
    print("The ChromaDB now contains the same products as the backend PostgreSQL database")
    print("You can now use the shopping assistant with proper product IDs!")

if __name__ == "__main__":
    asyncio.run(main())
