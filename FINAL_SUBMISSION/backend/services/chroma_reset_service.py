import logging
import asyncio

logger = logging.getLogger("chroma_reset_service")

def auto_check_chroma_dimension():
    """
    Checks if ChromaDB collections match the expected 384 dimensions for BGE-small.
    If a mismatch occurs, it drops the collections, recreates them, and triggers a re-index.
    """
    try:
        import chromadb
        from chromadb.config import Settings
        
        # We need to test the dimension
        client = chromadb.PersistentClient(path='backend/chroma_db', settings=Settings(anonymized_telemetry=False))
        coll = client.get_or_create_collection('maintenance_docs')
        
        test_id = "dim_test_init"
        
        # Test adding a 384-d vector
        try:
            coll.add(embeddings=[[0.0] * 384], documents=["test"], ids=[test_id])
            coll.delete(ids=[test_id])
            logger.info("ChromaDB dimensions verified (384).")
            return True
        except Exception as e:
            if "dimension" in str(e).lower() or "expected" in str(e).lower():
                logger.warning(f"Chroma dimension mismatch detected: {e}. Resetting collections...")
                
                # Delete old collections
                try:
                    client.delete_collection("maintenance_docs")
                except: pass
                
                try:
                    client.delete_collection("sandbox_knowledge")
                except: pass
                
                # Recreate
                client.create_collection("maintenance_docs")
                client.create_collection("sandbox_knowledge")
                logger.info("ChromaDB collections recreated.")
                
                # Re-index
                reindex_all_documents()
                return True
            else:
                logger.error(f"Unexpected ChromaDB error during check: {e}")
                return False

    except Exception as e:
        logger.error(f"Error checking chroma DB dimensions: {e}")
        return False


def reindex_all_documents():
    """
    Fetches all documents from the DB and re-embeds them using BGE.
    """
    try:
        from backend.database import SessionLocal
        import backend.models as models
        from backend.services.document_service import embed_company_document
        
        db = SessionLocal()
        docs = db.query(models.CompanyDocument).all()
        
        if not docs:
            logger.info("No existing documents to re-index.")
            db.close()
            return
            
        logger.info(f"Re-indexing {len(docs)} documents with new embedding model...")
        
        # Need to run async functions in a synchronous context
        loop = asyncio.get_event_loop()
        
        for doc in docs:
            logger.info(f"Re-indexing {doc.title} ({doc.id})...")
            # Re-embed
            loop.run_until_complete(embed_company_document(doc.file_path, doc.filename, doc.id))
            
        logger.info("Re-indexing complete!")
        db.close()
        
    except Exception as e:
        logger.error(f"Failed to re-index documents: {e}")
