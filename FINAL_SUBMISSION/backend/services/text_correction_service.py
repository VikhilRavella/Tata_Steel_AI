"""
Local Text Correction Service using Hugging Face Transformers.
Replaces the Gemini API-based text normalization with a local T5 grammar correction model.
Model: vennify/t5-base-grammar-correction
"""

import time
import re
import logging

logger = logging.getLogger("text_correction_service")

# =============================================
# MODEL SINGLETON (Cached in memory)
# =============================================
_tokenizer = None
_model = None
_model_loaded = False
_model_load_error = None

MAX_INPUT_LENGTH = 512  # T5 max token limit


def load_model():
    """
    Load the T5 grammar correction model into memory.
    Called once at application startup. Cached for all subsequent requests.
    """
    global _tokenizer, _model, _model_loaded, _model_load_error

    if _model_loaded:
        return True

    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

        logger.info("Loading text correction model: vennify/t5-base-grammar-correction ...")
        start = time.time()

        _tokenizer = AutoTokenizer.from_pretrained("vennify/t5-base-grammar-correction")
        _model = AutoModelForSeq2SeqLM.from_pretrained("vennify/t5-base-grammar-correction")

        _model_loaded = True
        _model_load_error = None
        elapsed = time.time() - start
        logger.info(f"Text correction model loaded successfully in {elapsed:.2f}s")
        print(f"\n[OK] Text Correction Model loaded in {elapsed:.2f}s\n")
        return True

    except Exception as e:
        _model_load_error = str(e)
        _model_loaded = False
        logger.error(f"Failed to load text correction model: {e}")
        print(f"\n[FAIL] Text Correction Model load failed: {e}\n")
        return False


def correct_text(text: str) -> str:
    """
    Correct grammar and spelling in the input text using the local T5 model.

    Args:
        text: Raw user text input

    Returns:
        Grammar-corrected text, or original text if correction fails.
    """
    # Guard: empty input
    if not text or not text.strip():
        return text

    # Guard: model not loaded
    if not _model_loaded or _tokenizer is None or _model is None:
        logger.warning("Text correction model not loaded. Returning original text.")
        return text

    try:
        start = time.time()
        clean_text = text.strip()

        # Guard: long text — truncate to safe limit
        if len(clean_text) > 1000:
            clean_text = clean_text[:1000]

        # Preserve codes (part numbers, equipment IDs, work order IDs)
        code_pattern = r'((?:PART|EQP|WO|EQ|ENG|SUP|MGR)-\d+)'
        codes_found = re.findall(code_pattern, clean_text, re.IGNORECASE)
        
        # Replace codes with placeholders to protect them
        placeholders = {}
        for i, code in enumerate(codes_found):
            placeholder = f"CODEPH{i}"
            placeholders[placeholder] = code
            clean_text = clean_text.replace(code, placeholder, 1)

        # Tokenize and generate
        input_ids = _tokenizer(
            clean_text,
            return_tensors="pt",
            max_length=MAX_INPUT_LENGTH,
            truncation=True
        ).input_ids

        outputs = _model.generate(
            input_ids,
            max_length=MAX_INPUT_LENGTH,
            num_beams=4,
            early_stopping=True
        )

        corrected = _tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Restore preserved codes
        for placeholder, code in placeholders.items():
            corrected = corrected.replace(placeholder, code)

        elapsed = time.time() - start

        print(f"\n--- LOCAL TEXT CORRECTION ---")
        print(f"Original Text: {text}")
        print(f"Corrected Text: {corrected}")
        print(f"Correction Time: {elapsed:.4f} seconds")
        print(f"-----------------------------\n")

        return corrected

    except Exception as e:
        logger.error(f"Text correction failed: {e}")
        return text


def get_model_status() -> dict:
    """Return the current status of the text correction model."""
    return {
        "model_name": "vennify/t5-base-grammar-correction",
        "loaded": _model_loaded,
        "error": _model_load_error
    }
