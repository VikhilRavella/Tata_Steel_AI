"""
Text Normalization Service — Local Model Edition.
Uses the local vennify/t5-base-grammar-correction model via text_correction_service
instead of the Gemini API for all grammar/spelling correction.
"""

import time
import re

# Vocabulary for Spellcheck (lower-cased)
STANDARD_VOCAB = {
    # Pronouns & helper verbs
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their",
    "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the",
    "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in",
    "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now",
    # Domain words
    "need", "oil", "filter", "supervisor", "engineer", "manager", "role", "department", "profile", "specialization",
    "certification", "shift", "roster", "equipment", "machine", "part", "parts", "inventory", "stock", "warehouse",
    "bin", "rack", "supplier", "vendor", "qty", "quantity", "cost", "price", "order", "orders", "task", "job", "card",
    "alert", "alerts", "notification", "notifications", "audit", "log", "logs", "safety", "checklist", "ppe", "loto",
    "lockout", "tagout", "permit", "signature", "document", "documents", "pdf", "text", "manual", "manuals", "sop",
    "sops", "report", "reports", "summary", "root", "cause", "rca", "failure", "defect", "cracks", "leak", "wear",
    "corrosion", "bearing", "valve", "motor", "pump", "compressor", "bolt", "bolts", "bearings", "filters", "valves",
    "motors", "pumps", "compressors", "seals", "seal", "gasket", "gaskets", "coupling", "couplings", "belt", "belts",
    "chain", "chains", "sensor", "sensors", "hi", "hello", "hey", "thanks", "thank", "ok", "okay", "bye", "goodbye",
    "yes", "no", "sure", "great", "nice", "cool", "got", "it", "understood", "who", "am", "help", "what", "can", "do",
    "spelling", "mistake", "error", "welcome", "about", "available", "show", "active", "pending", "approved", "rejected",
    "created", "by", "assigned", "to", "escalated", "resolved", "history", "chat", "session", "timeline", "file", "upload",
    "troubleshoot", "repair", "maintenance", "preventive", "corrective", "breakdown", "planned", "scheduled", "status",
    "normal", "warning", "critical", "danger", "hazard", "risk", "ppe", "loto", "breaker", "lock", "tag", "isolated",
    "insufficient", "delayed", "stock", "remaining", "current", "minimum", "reorder", "lead", "days", "contact"
}

def has_spelling_mistakes(text: str) -> bool:
    """
    Checks if the input text contains spelling mistakes.
    Filters out numbers, standard part/equipment/work-order codes, and punctuation.
    """
    # Clean the text into words
    words = re.findall(r"\b[a-zA-Z']+\b", text.lower())
    for word in words:
        # Ignore single letters except 'i', 'a'
        if len(word) <= 1 and word not in {"i", "a"}:
            continue
        # Check against vocabulary
        if word not in STANDARD_VOCAB:
            return True
    return False

def calculate_intent_confidence(text: str) -> float:
    """
    Calculates the confidence score of the matched intent (0.0 to 1.0).
    If no domain keywords are present and it falls into GENERAL_CHAT, confidence is low (e.g. 0.5).
    If it explicitly matches standard domain keywords, confidence is high (1.0).
    """
    msg_lower = text.lower()
    
    # Keyword categories from engineering_agent.py
    vision_inventory_keywords = ['suggest spare', 'replacement part', 'required part', 'replace', 'availability', 'create request', 'spare recommendation', 'spare part']
    pdf_keywords = ['hazards', 'warnings', 'ppe', 'procedure', 'maintenance', 'manual', 'equipment', 'parts', 'inspection', 'safety', 'loto', 'lockout', 'tagout', 'document', 'pdf', 'sop', 'guide', 'datasheet', 'specification', 'report', 'drawing']
    inventory_keywords = ['inventory', 'stock', 'spare', 'part', 'bearing', 'filter', 'gasket', 'seal', 'valve', 'motor', 'pump', 'gear', 'coupling', 'belt', 'chain', 'sensor', 'warehouse', 'bin', 'rack', 'supplier', 'vendor', 'material', 'bom']
    wo_keywords = ['work order', 'task', 'job card', 'schedule', 'service request', 'work request', 'planned maintenance', 'corrective maintenance', 'preventive', 'breakdown', 'pending work']
    supervisor_keywords = ['supervisor', 'manager', 'lead', 'reporting manager', 'approval', 'escalation', 'who is my']
    rca_keywords = ['root cause', 'rca', 'why did this fail', 'investigate', 'failure analysis', 'diagnose', 'troubleshoot']
    report_keywords = ['report', 'summary report', 'audit report', 'incident report', 'weekly report', 'daily report']
    safety_keywords = ['safety', 'hazard', 'risk', 'incident', 'near miss', 'unsafe', 'permit', 'hot work', 'confined space', 'electrical safety', 'leak', 'crack']
    memory_keywords = ['remember', 'memory', 'previous chat', 'last discussion', 'earlier conversation', 'history', 'recall', 'stored', 'project goal', 'preference']
    profile_keywords = ['my profile', 'my role', 'my department']
    casual_words = ['hello', 'hi', 'hey', 'good morning', 'good evening', 'good afternoon', 'how are you', 'thanks', 'thank you', 'ok', 'okay', 'bye', 'goodbye', 'yes', 'no', 'sure', 'great', 'nice', 'cool', 'got it', 'understood', 'who am i', 'help', 'what can you do', 'show profile']

    matched_categories = 0
    if any(k in msg_lower for k in vision_inventory_keywords): matched_categories += 1
    if any(k in msg_lower for k in pdf_keywords): matched_categories += 1
    if any(k in msg_lower for k in inventory_keywords): matched_categories += 1
    if any(k in msg_lower for k in wo_keywords): matched_categories += 1
    if any(k in msg_lower for k in supervisor_keywords): matched_categories += 1
    if any(k in msg_lower for k in rca_keywords): matched_categories += 1
    if any(k in msg_lower for k in report_keywords): matched_categories += 1
    if any(k in msg_lower for k in safety_keywords): matched_categories += 1
    if any(k in msg_lower for k in memory_keywords): matched_categories += 1
    if any(k in msg_lower for k in profile_keywords): matched_categories += 1
    if any(k in msg_lower for k in casual_words): matched_categories += 1

    # If it matches absolutely no known keywords, confidence is low (0.0)
    if matched_categories == 0:
        return 0.0
    # If it matches multiple conflicting intent keyword lists, confidence is lower (e.g. 0.6)
    if matched_categories > 1:
        return 0.6
    # If it matches exactly one category, confidence is high (1.0)
    return 1.0

async def normalize_user_text(text: str) -> str:
    """
    Normalizes spelling, grammar, and terminology using the LOCAL T5 model.
    Bypasses normalization if there are no spelling mistakes and intent confidence is >= 70%.
    """
    # Check optimization constraints
    has_error = has_spelling_mistakes(text)
    confidence = calculate_intent_confidence(text)
    
    if not has_error and confidence >= 0.7:
        # Skip normalization
        return text

    start_time = time.time()

    try:
        from backend.services.text_correction_service import correct_text
        corrected = correct_text(text)
        
        duration = time.time() - start_time
        print("\n--- LOCAL TEXT NORMALIZATION ---")
        print(f"Original Text: {text}")
        print(f"Normalized Text: {corrected}")
        print(f"Normalization Time: {duration:.4f} seconds")
        print("---------------------------------\n")
        
        return corrected

    except Exception as e:
        print(f"Local Text Normalization error: {e}")

    # Fallback to original text if anything fails
    duration = time.time() - start_time
    print("\n--- LOCAL TEXT NORMALIZATION (FALLBACK) ---")
    print(f"Original Text: {text}")
    print(f"Normalized Text: {text} (Fallback)")
    print(f"Normalization Time: {duration:.4f} seconds")
    print("---------------------------------\n")
    return text
