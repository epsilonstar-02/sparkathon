import sqlite3
import chromadb

def main():
    print('=== SQLite Database Verification ===')
    conn = sqlite3.connect('walmart_products.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM products')
    count = cursor.fetchone()[0]
    print(f'SQLite products count: {count}')
    cursor.execute('SELECT name, type, price FROM products LIMIT 3')
    samples = cursor.fetchall()
    print('Sample products:')
    for name, type_val, price in samples:
        print(f'  - {name} ({type_val}) - ${price}')
    conn.close()
    print('\n=== ChromaDB Verification ===')
    client = chromadb.PersistentClient(path='./chroma_db')
    collection = client.get_collection('walmart_products')
    print(f'ChromaDB products count: {collection.count()}')
    results = collection.query(
        query_texts=['laptop computer'],
        n_results=3,
        include=['metadatas', 'distances']
    )
    print('Sample semantic search for "laptop computer":')
    for i, (metadata, distance) in enumerate(zip(results['metadatas'][0], results['distances'][0])):
        score = 1 - distance
        print(f'  {i+1}. {metadata["name"]} ({metadata["category"]}) - Score: {score:.3f}')
    print('\n✅ Both databases are working correctly!')

if __name__ == '__main__':
    main()