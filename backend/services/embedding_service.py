"""
Local Embedding Service using Hugging Face Transformers.
Model: BAAI/bge-small-en-v1.5
"""

import time
import logging

logger = logging.getLogger("embedding_service")

# =============================================
# MODEL SINGLETON (Cached in memory)
# =============================================
_tokenizer = None
_model = None
_device = "cpu"
_model_loaded = False
_model_load_error = None

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSION = 384


def load_embedding_model():
    """
    Load the BGE embedding model into memory.
    Called once at application startup. Cached globally.
    """
    global _tokenizer, _model, _device, _model_loaded, _model_load_error

    if _model_loaded:
        return True

    try:
        from transformers import AutoTokenizer, AutoModel
        import torch

        _device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(f"Loading embedding model: {MODEL_NAME} on {_device.upper()} ...")
        start = time.time()

        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModel.from_pretrained(MODEL_NAME)
        _model.eval()
        _model.to(_device)

        _model_loaded = True
        _model_load_error = None
        elapsed = time.time() - start
        
        print("\n==================================================")
        print("EMBEDDING MODEL STARTUP")
        print(f"Embedding Model: {MODEL_NAME}")
        print(f"Embedding Dimension: {EMBEDDING_DIMENSION}")
        print(f"Device: {_device.upper()}")
        print(f"Load Time: {elapsed:.2f}s")
        print("==================================================\n")
        
        return True

    except Exception as e:
        _model_load_error = str(e)
        _model_loaded = False
        logger.error(f"Failed to load embedding model: {e}")
        print(f"\n[FAIL] Embedding Model load failed: {e}\n")
        return False


def generate_embedding(text: str) -> list[float]:
    """
    Generate a 384-dimensional embedding vector for the input text using BGE.
    """
    if not _model_loaded or _model is None or _tokenizer is None:
        # Fallback if model not loaded
        return [0.0] * EMBEDDING_DIMENSION

    try:
        import torch
        # Tokenize sentences
        encoded_input = _tokenizer([text], padding=True, truncation=True, max_length=512, return_tensors='pt').to(_device)
        
        # Compute token embeddings
        with torch.no_grad():
            model_output = _model(**encoded_input)
            
        # Perform pooling. For BGE, the [CLS] token is used as the sentence embedding.
        sentence_embeddings = model_output[0][:, 0]
        
        # Normalize embeddings
        sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
        
        # Convert to list of floats
        return sentence_embeddings[0].cpu().tolist()

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return [0.0] * EMBEDDING_DIMENSION


def generate_embeddings(texts: list[str], batch_size: int = 16) -> list[list[float]]:
    """
    Generate embeddings for a list of text chunks in batches to prevent CPU/memory spikes.
    """
    if not texts:
        return []
        
    if not _model_loaded or _model is None or _tokenizer is None:
        return [[0.0] * EMBEDDING_DIMENSION for _ in texts]

    all_embeddings = []
    try:
        import torch
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Tokenize batch
            encoded_input = _tokenizer(batch_texts, padding=True, truncation=True, max_length=512, return_tensors='pt').to(_device)
            
            # Compute token embeddings
            with torch.no_grad():
                model_output = _model(**encoded_input)
                
            # Perform pooling (CLS token)
            sentence_embeddings = model_output[0][:, 0]
            
            # Normalize embeddings
            sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
            
            all_embeddings.extend(sentence_embeddings.cpu().tolist())
            
        return all_embeddings

    except Exception as e:
        logger.error(f"Batch embedding generation failed: {e}")
        # If partial success, pad the rest with zeros, otherwise return all zeros
        if len(all_embeddings) < len(texts):
            all_embeddings.extend([[0.0] * EMBEDDING_DIMENSION] * (len(texts) - len(all_embeddings)))
        return all_embeddings
