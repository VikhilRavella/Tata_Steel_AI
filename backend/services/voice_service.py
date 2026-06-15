import time
import asyncio
from faster_whisper import WhisperModel

# Load model globally to avoid reloading on every request
# Using 'base' model as requested for improved accuracy in Indian languages and engineering terminology
print("Loading Whisper model (base)...")
try:
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    print("Whisper model loaded successfully.")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    whisper_model = None

async def process_voice_input(audio_file_path: str):
    """
    Processes audio using faster-whisper.
    Returns (transcription, detected_language, metrics_dict)
    """
    if not whisper_model:
        raise Exception("Whisper model is not available.")

    start_time = time.time()
    
    # Run in a separate thread so we don't block the async event loop
    def _transcribe():
        # task="transcribe" preserves the original language
        segments, info = whisper_model.transcribe(audio_file_path, beam_size=5, task="transcribe")
        transcription = " ".join([segment.text for segment in segments])
        return transcription, info

    transcription, info = await asyncio.to_thread(_transcribe)
    
    transcription_time = time.time() - start_time
    
    metrics = {
        "detected_language": info.language,
        "language_probability": info.language_probability,
        "speech_length": info.duration,
        "transcription_time": transcription_time
    }
    
    return transcription.strip(), info.language, metrics
