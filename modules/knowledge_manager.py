import os
import glob
import re
import math
from collections import Counter
from typing import Dict, Any, List, Optional
from modules.logger import setup_logger

logger = setup_logger("KnowledgeManager")

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "knowledge")

class DocumentChunk:
    def __init__(self, doc_name: str, text: str, chunk_id: int):
        self.doc_name = doc_name
        self.text = text.strip()
        self.chunk_id = chunk_id
        self.tokens = self._tokenize(self.text)
        self.term_freq = Counter(self.tokens)

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\w+', text) if len(w) > 2]

class LocalKnowledgeManager:
    """Local Document Knowledge Base (RAG) for personal notes, manuals, and code files."""
    def __init__(self, knowledge_dir: Optional[str] = None):
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        os.makedirs(self.knowledge_dir, exist_ok=True)
        self.chunks: List[DocumentChunk] = []
        self.doc_frequencies = Counter()
        self.total_docs = 0
        self.reload_documents()

    def reload_documents(self):
        """Scans data/knowledge/ directory and builds local semantic index."""
        self.chunks = []
        self.doc_frequencies = Counter()
        supported_exts = ["*.txt", "*.md", "*.json", "*.csv", "*.log", "*.py", "*.js", "*.html"]
        
        file_paths = []
        for ext in supported_exts:
            file_paths.extend(glob.glob(os.path.join(self.knowledge_dir, ext)))
            file_paths.extend(glob.glob(os.path.join(self.knowledge_dir, "**", ext), recursive=True))

        for file_path in set(file_paths):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                doc_name = os.path.relpath(file_path, self.knowledge_dir)
                # Split content into sensible 400-word chunks
                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                
                chunk_id = 0
                for para in paragraphs:
                    if len(para) < 20:
                        continue
                    chunk = DocumentChunk(doc_name, para, chunk_id)
                    self.chunks.append(chunk)
                    # Update document frequencies
                    for term in set(chunk.tokens):
                        self.doc_frequencies[term] += 1
                    chunk_id += 1
            except Exception as e:
                logger.error(f"Error indexing knowledge doc '{file_path}': {e}")

        self.total_docs = len(self.chunks)
        logger.info(f"📚 Local Knowledge Base indexed {len(file_paths)} files ({self.total_docs} chunks) from '{self.knowledge_dir}'")

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Searches indexed documents using BM25-style TF-IDF ranking."""
        if not query.strip() or not self.chunks:
            return []

        query_tokens = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 2]
        if not query_tokens:
            return []

        scored_chunks = []
        k1 = 1.5
        b = 0.75
        avg_dl = sum(len(c.tokens) for c in self.chunks) / max(1, self.total_docs)

        for chunk in self.chunks:
            score = 0.0
            doc_len = len(chunk.tokens)
            
            for q in query_tokens:
                if q in chunk.term_freq:
                    tf = chunk.term_freq[q]
                    df = self.doc_frequencies.get(q, 1)
                    idf = math.log(1 + (self.total_docs - df + 0.5) / (df + 0.5))
                    score += idf * ((tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_dl))))

            if score > 0.1:
                scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, chunk in scored_chunks[:top_k]:
            results.append({
                "score": round(score, 3),
                "document": chunk.doc_name,
                "text": chunk.text
            })
        return results

    def add_document(self, filename: str, content: str) -> str:
        """Adds or writes a new document into the knowledge directory and reloads index."""
        safe_name = re.sub(r'[^a-zA-Z0-9_\.-]', '_', filename)
        if not safe_name.endswith((".txt", ".md")):
            safe_name += ".md"
        
        target_path = os.path.join(self.knowledge_dir, safe_name)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        self.reload_documents()
        logger.info(f"Added document '{safe_name}' to Knowledge Base.")
        return target_path

    def get_knowledge_context(self, task_goal: str) -> str:
        """Finds relevant knowledge snippets to include in LLM prompt context."""
        hits = self.search(task_goal, top_k=2)
        if not hits:
            return ""
        
        blocks = []
        for hit in hits:
            blocks.append(f"• [From {hit['document']}]: {hit['text']}")
        return "--- RELEVANT LOCAL KNOWLEDGE BASE EXCERPTS ---\n" + "\n\n".join(blocks) + "\n-----------------------------------------------"
