"""
RAG Pipeline for Repository Analysis
Uses LangChain + ChromaDB for in-memory vector storage
"""

from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from pathlib import Path


class RAGPipeline:
    """RAG pipeline for code repository analysis."""
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize the RAG pipeline.
        
        Args:
            embedding_model: HuggingFace model name for embeddings
        """
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            length_function=len,
            separators=[
                "\nclass ", "\ndef ", "\nasync def ",  # Python
                "\nfunction ", "\nconst ", "\nexport ",  # JavaScript
                "\npublic ", "\nprivate ", "\nprotected ",  # Java/C#
                "\n\n", "\n", " ", ""
            ]
        )
    
    def _get_file_type(self, file_path: str) -> str:
        """Determine file type from path."""
        ext = Path(file_path).suffix.lower()
        
        type_mapping = {
            '.py': 'python',
            '.js': 'javascript', '.jsx': 'javascript', '.ts': 'typescript', '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.c': 'c', '.cpp': 'cpp', '.h': 'c_header', '.hpp': 'cpp_header',
            '.cs': 'csharp',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.html': 'html', '.css': 'css', '.scss': 'scss',
            '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml',
            '.md': 'markdown', '.txt': 'text', '.rst': 'rst',
            '.sql': 'sql',
            '.sh': 'shell', '.bash': 'shell',
            '.dockerfile': 'dockerfile'
        }
        
        return type_mapping.get(ext, 'unknown')
    
    def _create_documents(self, files: Dict[str, Dict[str, Any]]) -> List[Document]:
        """Convert repository files to LangChain documents."""
        documents = []
        
        for file_path, file_data in files.items():
            content = file_data['content']
            file_type = self._get_file_type(file_path)
            
            # Create metadata
            metadata = {
                'source': file_path,
                'file_type': file_type,
                'size': file_data['size'],
                'directory': str(Path(file_path).parent),
                'filename': Path(file_path).name
            }
            
            # Split large files into chunks
            if len(content) > 1500:
                chunks = self.text_splitter.split_text(content)
                for i, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata['chunk_index'] = i
                    chunk_metadata['total_chunks'] = len(chunks)
                    documents.append(Document(page_content=chunk, metadata=chunk_metadata))
            else:
                documents.append(Document(page_content=content, metadata=metadata))
        
        return documents
    
    def build_index(self, files: Dict[str, Dict[str, Any]]) -> int:
        """
        Build the vector index from repository files.
        
        Args:
            files: Dictionary of file paths to file data
            
        Returns:
            Number of documents indexed
        """
        documents = self._create_documents(files)
        
        if not documents:
            raise ValueError("No documents to index")
        
        # Create in-memory ChromaDB vectorstore
        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name="repo_analysis"
        )
        
        return len(documents)
    
    def query(self, query: str, k: int = 5, filter_dict: Dict = None) -> List[Document]:
        """
        Query the vector store for relevant documents.
        
        Args:
            query: Search query
            k: Number of results to return
            filter_dict: Optional metadata filter
            
        Returns:
            List of relevant documents
        """
        if not self.vectorstore:
            raise ValueError("Index not built. Call build_index first.")
        
        if filter_dict:
            results = self.vectorstore.similarity_search(query, k=k, filter=filter_dict)
        else:
            results = self.vectorstore.similarity_search(query, k=k)
        
        return results
    
    def query_with_scores(self, query: str, k: int = 5) -> List[tuple]:
        """
        Query with relevance scores.
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            List of (document, score) tuples
        """
        if not self.vectorstore:
            raise ValueError("Index not built. Call build_index first.")
        
        return self.vectorstore.similarity_search_with_score(query, k=k)
    
    def get_file_context(self, file_path: str) -> str:
        """
        Get all content for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Combined content from all chunks of the file
        """
        results = self.query(
            query=f"file: {file_path}",
            k=20,
            filter_dict={'source': file_path}
        )
        
        # Sort by chunk index and combine
        sorted_results = sorted(results, key=lambda d: d.metadata.get('chunk_index', 0))
        return "\n".join([doc.page_content for doc in sorted_results])
    
    def get_architecture_context(self, k: int = 10) -> str:
        """
        Get context relevant for architecture understanding.
        
        Args:
            k: Number of results per query
            
        Returns:
            Combined relevant context
        """
        queries = [
            "main entry point application initialization",
            "API routes endpoints handlers",
            "database models schema",
            "configuration settings environment",
            "core business logic services",
            "imports dependencies modules"
        ]
        
        all_docs = []
        seen_sources = set()
        
        for query in queries:
            results = self.query(query, k=k)
            for doc in results:
                source = doc.metadata.get('source', '')
                if source not in seen_sources:
                    seen_sources.add(source)
                    all_docs.append(doc)
        
        # Format context
        context_parts = []
        for doc in all_docs[:15]:  # Limit total context
            source = doc.metadata.get('source', 'unknown')
            context_parts.append(f"=== {source} ===\n{doc.page_content}\n")
        
        return "\n".join(context_parts)
    
    def get_file_structure(self, files: Dict[str, Dict[str, Any]]) -> str:
        """
        Generate a file structure overview.
        
        Args:
            files: Dictionary of files
            
        Returns:
            Tree-like structure string
        """
        paths = sorted(files.keys())
        
        # Group by directory
        structure = {}
        for path in paths:
            parts = Path(path).parts
            current = structure
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = None  # File marker
        
        def format_tree(tree: dict, prefix: str = "") -> str:
            lines = []
            items = list(tree.items())
            for i, (name, subtree) in enumerate(items):
                is_last = i == len(items) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{name}")
                if subtree is not None:  # Directory
                    extension = "    " if is_last else "│   "
                    lines.append(format_tree(subtree, prefix + extension))
            return "\n".join(lines)
        
        return format_tree(structure)
