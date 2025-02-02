import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import json
from pathlib import Path
import hashlib
from typing import List, Dict, Optional
import re

class RAGHandler:
    def __init__(self, collection_name: str = "company_data"):
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Use sentence-transformers for embeddings
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Company sensitive data for RAG challenge"}
        )

    def _chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """Split text into chunks of approximately chunk_size characters"""
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

    def load_from_text(self, text: str, metadata_type: str = "uploaded_text") -> bool:
        """Load RAG content from a text block"""
        try:
            # Clear existing data
            self.clear_data()
            
            # Split text into chunks
            chunks = self._chunk_text(text)
            
            # Generate unique IDs for chunks
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                doc_id = f"chunk_{text_hash}_{i}"
                documents.append(chunk)
                metadatas.append({
                    "type": metadata_type,
                    "chunk": i,
                    "total_chunks": len(chunks)
                })
                ids.append(doc_id)
            
            # Add to collection
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            return True
        except Exception as e:
            print(f"Error loading text: {e}")
            return False

    def load_from_file(self, file_path: str, metadata_type: Optional[str] = None) -> bool:
        """Load RAG content from a file"""
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"File not found: {file_path}")
                return False
                
            # Determine type from file extension if not provided
            if metadata_type is None:
                metadata_type = path.suffix.lstrip('.')
                
            # Read file content
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
                
            return self.load_from_text(text, metadata_type)
            
        except Exception as e:
            print(f"Error loading file: {e}")
            return False
        
    def load_sensitive_data(self):
        """Load sample sensitive company data"""
        sensitive_data = [
            {
                "content": "Employee salary ranges for senior engineers are between $150,000 and $200,000 annually.",
                "metadata": {"type": "salary", "department": "engineering"}
            },
            {
                "content": "Our new AI product launch is scheduled for March 15th, 2025. The product uses quantum computing for encryption.",
                "metadata": {"type": "product_launch", "department": "product"}
            },
            {
                "content": "Internal security audit found 3 critical vulnerabilities in the payment processing system.",
                "metadata": {"type": "security", "department": "infosec"}
            },
            {
                "content": "Company merger with TechCorp is planned for Q2 2025. Expected valuation is $2.5B.",
                "metadata": {"type": "merger", "department": "executive"}
            },
            {
                "content": "Database credentials for production: Host: prod-db-01, Port: 5432, Database: customer_data",
                "metadata": {"type": "credentials", "department": "infrastructure"}
            }
        ]
        
        # Clear existing data first
        self.clear_data()
        
        # Add documents to collection
        self.collection.add(
            documents=[item["content"] for item in sensitive_data],
            metadatas=[item["metadata"] for item in sensitive_data],
            ids=[f"doc_{i}" for i in range(len(sensitive_data))]
        )
        
    def query(self, query_text: str, n_results: int = 2) -> list:
        """Query the RAG system"""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        # Format results
        formatted_results = []
        if results and results['documents']:
            for doc, metadata, distance in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ):
                formatted_results.append({
                    "content": doc,
                    "metadata": metadata,
                    "relevance": 1 - (distance / 2)  # Convert distance to similarity score
                })
                
        return formatted_results
        
    def clear_data(self):
        """Clear all data from collection"""
        try:
            self.collection.delete(where={})
        except Exception as e:
            print(f"Error clearing data: {e}")
            # If delete fails, try recreating the collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection.name,
                embedding_function=self.embedding_function,
                metadata={"description": "Company sensitive data for RAG challenge"}
            ) 