import os
import base64
from io import BytesIO
import json
import logging
from PIL import Image
import torch

try:
    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Constants
MODEL_NAME = "Qwen/Qwen3-VL-8B-Instruct"

# Global lazy-loaded instances
_model = None
_processor = None

def load_vision_model():
    """
    Lazy loads the Qwen3-VL model.
    Falls back to CPU if GPU VRAM is insufficient or CUDA is unavailable.
    """
    global _model, _processor
    
    if not TRANSFORMERS_AVAILABLE:
        logger.error("Transformers library is not available. Cannot load vision model.")
        return False
        
    if _model is not None and _processor is not None:
        return True # Already loaded

    logger.info(f"Loading Vision Model: {MODEL_NAME}")
    try:
        # Check device availability
        if torch.cuda.is_available():
            device = "cuda"
            # Optimization for 8B model: load in 8-bit or float16 to save VRAM if possible.
            # Using bfloat16 for RTX 30 series, fallback to float16.
            dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        else:
            device = "cpu"
            dtype = torch.float32

        logger.info(f"Using device: {device} with dtype: {dtype}")

        _model = Qwen2VLForConditionalGeneration.from_pretrained(
            MODEL_NAME, 
            torch_dtype=dtype, 
            device_map="auto" if device == "cuda" else None
        )
        if device == "cpu":
            _model.to("cpu")
            
        _processor = AutoProcessor.from_pretrained(MODEL_NAME)
        logger.info("Vision Model loaded successfully.")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load vision model: {e}")
        _model = None
        _processor = None
        return False

def analyze_equipment_image(image_base64: str, prompt: str) -> str:
    """
    Analyzes an equipment image using the Hugging Face Qwen3-VL-8B-Instruct model.
    Returns a structured JSON response.
    """
    global _model, _processor
    
    # 1. Lazy load the model if not loaded
    if not load_vision_model():
        return json.dumps({
            "equipment_type": "Unknown",
            "detected_defects": ["Vision analysis failed - model could not be loaded."],
            "risk_level": "UNKNOWN",
            "root_cause": "System Error",
            "recommendations": ["Manual inspection required."],
            "safety_notes": ["AI Vision subsystem is offline."]
        })

    # 2. Decode base64 to PIL Image
    try:
        raw_b64 = image_base64
        if raw_b64.startswith("data:image"):
            raw_b64 = raw_b64.split(",", 1)[1]
        
        image_bytes = base64.b64decode(raw_b64)
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        logger.error(f"Image decode error: {e}")
        return json.dumps({
            "equipment_type": "Error",
            "detected_defects": [f"Image processing failed: {str(e)}"],
            "risk_level": "UNKNOWN",
            "root_cause": "Invalid Image",
            "recommendations": ["Re-upload a clear image of the equipment."],
            "safety_notes": []
        })

    # 3. Construct Industrial Prompt Template
    vision_prompt = f"""You are an Industrial Maintenance Engineer.
Analyze the uploaded equipment image.

Identify:
• Equipment Type
• Visible Defects
• Cracks
• Corrosion
• Wear
• Leakage
• Misalignment
• Equipment Condition

Generate:
• Risk Level
• Root Cause Analysis
• Maintenance Recommendation
• Safety Considerations
• Next Actions

User's Query: {prompt}

Return ONLY a raw JSON object matching the following structure without any markdown blocks or explanations:
{{
    "equipment_type": "string",
    "detected_defects": ["string"],
    "risk_level": "string",
    "root_cause": "string",
    "recommendations": ["string"],
    "safety_notes": ["string"]
}}"""

    # 4. Build multimodal message
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": vision_prompt},
            ],
        }
    ]

    try:
        # Preparation for inference
        text = _processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        # If the processor expects a list of PIL images:
        image_inputs, video_inputs = None, None
        try:
            from qwen_vl_utils import process_vision_info
            image_inputs, video_inputs = process_vision_info(messages)
        except ImportError:
            image_inputs = [image]

        inputs = _processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(_model.device)

        # 5. Generate response
        with torch.no_grad():
            generated_ids = _model.generate(
                **inputs, 
                max_new_tokens=512,
                temperature=0.2,
                do_sample=True
            )
            
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        
        output_text = _processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        
        # Strip potential markdown formatting that model might add despite instructions
        cleaned_output = output_text.strip()
        if cleaned_output.startswith("```json"):
            cleaned_output = cleaned_output[7:]
        elif cleaned_output.startswith("```"):
            cleaned_output = cleaned_output[3:]
        if cleaned_output.endswith("```"):
            cleaned_output = cleaned_output[:-3]
            
        # Verify it parses as JSON, otherwise fallback
        try:
            json.loads(cleaned_output.strip())
            return cleaned_output.strip()
        except json.JSONDecodeError:
            # Output wasn't pure JSON, return a wrapper
            return json.dumps({
                "equipment_type": "Parsed Error",
                "detected_defects": ["Vision model responded with unstructured text."],
                "risk_level": "UNKNOWN",
                "root_cause": cleaned_output[:100],
                "recommendations": ["Review the raw output or re-prompt."],
                "safety_notes": []
            })
            
    except Exception as e:
        logger.error(f"Vision inference failed: {e}")
        return json.dumps({
            "equipment_type": "Inference Error",
            "detected_defects": [f"Model generation failed: {str(e)}"],
            "risk_level": "UNKNOWN",
            "root_cause": "Inference Exception",
            "recommendations": ["Check server logs for memory or hardware issues."],
            "safety_notes": ["AI Vision subsystem encountered a critical error."]
        })
