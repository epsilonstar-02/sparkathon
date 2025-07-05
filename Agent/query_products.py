#!/usr/bin/env python3
"""
ChromaDB Query Interface for Product Search
This script provides a simple interface to search products in the ChromaDB vector database.
"""

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import json

class ProductSearcher:
    def __init__(self, chroma_db_path: str = "./chroma_db"):
        """
        Initialize the Product Searcher
        
        Args:
            chroma_db_path: Path where ChromaDB data is stored
        """
        self.chroma_db_path = chroma_db_path
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=chroma_db_path)
        
        # Get the products collection
        try:
            self.collection = self.client.get_collection("products")
            print(f"Connected to products collection with {self.collection.count()} items")
        except Exception as e:
            print(f"Error: Could not connect to products collection: {e}")
            print("Please run ingest_products.py first to create the database.")
            raise
        
        # Initialize embedding model (same as used during ingestion)
        print("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Ready for searches!")
    
    def search(self, 
               query: str, 
               n_results: int = 5,
               filter_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Search for products using natural language query
        
        Args:
            query: Natural language search query
            n_results: Number of results to return
            filter_metadata: Optional metadata filters (e.g., {"category": "Video Game Consoles"})
            
        Returns:
            Dictionary containing search results
        """
        # Perform the search
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filter_metadata
        )
        
        return {
            'query': query,
            'n_results': len(results['ids'][0]),
            'results': [
                {
                    'id': doc_id,
                    'document': document,
                    'metadata': metadata,
                    'distance': distance
                }
                for doc_id, document, metadata, distance in zip(
                    results['ids'][0],
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )
            ]
        }
    
    def search_by_category(self, category: str, n_results: int = 10) -> Dict[str, Any]:
        """
        Search products by category
        
        Args:
            category: Product category to search for
            n_results: Number of results to return
            
        Returns:
            Dictionary containing search results
        """
        return self.search(
            query=f"products in {category} category",
            n_results=n_results,
            filter_metadata={"category": category}
        )
    
    def search_by_price_range(self, 
                              min_price: float, 
                              max_price: float, 
                              query: str = "",
                              n_results: int = 10) -> Dict[str, Any]:
        """
        Search products within a price range
        
        Args:
            min_price: Minimum price
            max_price: Maximum price
            query: Optional search query
            n_results: Number of results to return
            
        Returns:
            Dictionary containing search results
        """
        # Note: ChromaDB's where clause supports simple filters
        # For complex price range queries, we'll filter results after retrieval
        results = self.search(query=query or "products", n_results=n_results * 2)
        
        # Filter by price range
        filtered_results = []
        for result in results['results']:
            price = result['metadata'].get('price')
            if price is not None and min_price <= price <= max_price:
                filtered_results.append(result)
                if len(filtered_results) >= n_results:
                    break
        
        return {
            'query': f"{query} (price: ${min_price}-${max_price})",
            'n_results': len(filtered_results),
            'results': filtered_results
        }
    
    def get_available_categories(self) -> List[str]:
        """Get all available product categories"""
        # Get a sample of products to find categories
        results = self.collection.get(limit=1000)  # Get more items to find all categories
        categories = set()
        
        for metadata in results['metadatas']:
            if 'category' in metadata:
                categories.add(metadata['category'])
        
        return sorted(list(categories))
    
    def format_results(self, search_results: Dict[str, Any]) -> str:
        """
        Format search results for display
        
        Args:
            search_results: Results from search method
            
        Returns:
            Formatted string representation of results
        """
        output = []
        output.append(f"Search Query: {search_results['query']}")
        output.append(f"Found {search_results['n_results']} results")
        output.append("-" * 80)
        
        for i, result in enumerate(search_results['results'], 1):
            metadata = result['metadata']
            document = result['document']
            
            # Extract product name from document
            product_name = document.split('|')[0].replace('Product: ', '') if '|' in document else 'Unknown'
            
            output.append(f"{i}. {metadata.get('brand', 'Unknown Brand')} - {product_name}")
            output.append(f"   Category: {metadata.get('category', 'Unknown')}")
            output.append(f"   Price: ${metadata.get('price', 'N/A')} {metadata.get('currency', '')}")
            output.append(f"   Rating: {metadata.get('rating', 'N/A')}/5")
            output.append(f"   Availability: {metadata.get('availability', 'Unknown')}")
            output.append(f"   ID: {result['id']}")
            
            if 'distance' in result:
                output.append(f"   Similarity Score: {1 - result['distance']:.3f}")
            
            output.append("")
        
        return "\n".join(output)


def interactive_search():
    """Interactive search interface"""
    try:
        searcher = ProductSearcher()
    except Exception:
        return
    
    print("\n" + "="*80)
    print("CHROMADB PRODUCT SEARCH INTERFACE")
    print("="*80)
    print("Available commands:")
    print("  search <query>           - Search products by natural language")
    print("  category <category>      - Search by category")
    print("  price <min> <max> <query> - Search by price range")
    print("  categories               - List all available categories")
    print("  quit                     - Exit")
    print("="*80)
    
    while True:
        try:
            user_input = input("\nEnter command: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            parts = user_input.split(' ', 1)
            command = parts[0].lower()
            
            if command == 'search':
                if len(parts) < 2:
                    print("Usage: search <query>")
                    continue
                
                query = parts[1]
                results = searcher.search(query, n_results=5)
                print(searcher.format_results(results))
            
            elif command == 'category':
                if len(parts) < 2:
                    print("Usage: category <category>")
                    continue
                
                category = parts[1]
                results = searcher.search_by_category(category, n_results=5)
                print(searcher.format_results(results))
            
            elif command == 'price':
                if len(parts) < 2:
                    print("Usage: price <min> <max> [query]")
                    continue
                
                price_parts = parts[1].split()
                if len(price_parts) < 2:
                    print("Usage: price <min> <max> [query]")
                    continue
                
                try:
                    min_price = float(price_parts[0])
                    max_price = float(price_parts[1])
                    query = ' '.join(price_parts[2:]) if len(price_parts) > 2 else ""
                    
                    results = searcher.search_by_price_range(min_price, max_price, query, n_results=5)
                    print(searcher.format_results(results))
                except ValueError:
                    print("Invalid price values. Please enter numbers.")
            
            elif command == 'categories':
                categories = searcher.get_available_categories()
                print(f"\nAvailable categories ({len(categories)}):")
                for category in categories:
                    print(f"  - {category}")
            
            else:
                print(f"Unknown command: {command}")
                print("Available commands: search, category, price, categories, quit")
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    interactive_search()
