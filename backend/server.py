from fastapi import FastAPI, APIRouter, HTTPException, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal
import uuid
from datetime import datetime, timezone
import base64
import io
import numpy as np
import librosa
import soundfile as sf
from scipy import stats
import tempfile


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Valid API Key
VALID_API_KEY = "sk_test_voice_detection_2026"

# Define Models
class VoiceDetectionRequest(BaseModel):
    language: Literal["Tamil", "English", "Hindi", "Malayalam", "Telugu"]
    audioFormat: str = "mp3"
    audioBase64: str

class VoiceDetectionResponse(BaseModel):
    status: str
    language: str
    classification: Literal["AI_GENERATED", "HUMAN"]
    confidenceScore: float
    explanation: str

class ErrorResponse(BaseModel):
    status: str
    message: str


def analyze_audio_features(audio_data: bytes) -> tuple[str, float, str]:
    """
    Analyze audio features to detect AI-generated vs human voice.
    Returns: (classification, confidence_score, explanation)
    """
    try:
        # Create temporary file to load audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        # Load audio file
        y, sr = librosa.load(temp_path, sr=None, duration=30)  # Load up to 30 seconds
        
        # Clean up temp file
        os.unlink(temp_path)
        
        # Extract features
        # 1. Pitch variation (AI voices tend to have less natural variation)
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        
        pitch_std = np.std(pitch_values) if len(pitch_values) > 0 else 0
        
        # 2. Zero Crossing Rate (speech naturalness)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        zcr_mean = np.mean(zcr)
        zcr_std = np.std(zcr)
        
        # 3. Spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        
        spectral_centroid_std = np.std(spectral_centroids)
        spectral_rolloff_std = np.std(spectral_rolloff)
        
        # 4. MFCCs (Mel-frequency cepstral coefficients)
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_std = np.mean([np.std(mfcc) for mfcc in mfccs])
        
        # 5. Energy variation
        rms = librosa.feature.rms(y=y)[0]
        rms_std = np.std(rms)
        
        # 6. Spectral contrast (AI voices have less dynamic contrast)
        spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
        contrast_std = np.mean([np.std(sc) for sc in spectral_contrast])
        
        # Calculate AI probability score
        # Lower variation = higher AI probability
        ai_indicators = []
        explanations = []
        
        # Pitch consistency check (AI voices are too consistent)
        if pitch_std < 50:
            ai_indicators.append(0.8)
            explanations.append("Unnatural pitch consistency detected")
        elif pitch_std < 100:
            ai_indicators.append(0.5)
            explanations.append("Moderate pitch variation")
        else:
            ai_indicators.append(0.2)
            explanations.append("Natural pitch variation")
        
        # Zero crossing rate consistency
        if zcr_std < 0.02:
            ai_indicators.append(0.7)
            explanations.append("Robotic speech patterns")
        else:
            ai_indicators.append(0.3)
        
        # Spectral variation
        if spectral_centroid_std < 200:
            ai_indicators.append(0.75)
            explanations.append("Low spectral dynamics")
        else:
            ai_indicators.append(0.25)
        
        # Energy dynamics
        if rms_std < 0.02:
            ai_indicators.append(0.7)
            explanations.append("Uniform energy distribution")
        else:
            ai_indicators.append(0.3)
        
        # Spectral contrast
        if contrast_std < 5:
            ai_indicators.append(0.65)
            explanations.append("Flat tonal quality")
        else:
            ai_indicators.append(0.35)
        
        # Calculate final confidence
        ai_probability = np.mean(ai_indicators)
        
        # Determine classification
        if ai_probability > 0.5:
            classification = "AI_GENERATED"
            confidence = ai_probability
            main_explanation = ", ".join([e for e in explanations if "Natural" not in e][:2])
        else:
            classification = "HUMAN"
            confidence = 1 - ai_probability
            main_explanation = "Natural speech characteristics and human-like variations detected"
        
        return classification, round(confidence, 2), main_explanation
        
    except Exception as e:
        logging.error(f"Audio analysis error: {str(e)}")
        # Default to human with low confidence if analysis fails
        return "HUMAN", 0.55, "Unable to analyze audio features completely, defaulting to human classification"


# Routes
@api_router.get("/")
async def root():
    return {"message": "AI Voice Detection API v1.0"}


@api_router.post("/voice-detection", response_model=VoiceDetectionResponse)
async def detect_voice(
    request: VoiceDetectionRequest,
    x_api_key: str = Header(None, alias="x-api-key")
):
    """
    Detect if voice is AI-generated or human.
    Requires valid API key in x-api-key header.
    """
    # Validate API key
    if not x_api_key or x_api_key != VALID_API_KEY:
        raise HTTPException(
            status_code=401,
            detail={"status": "error", "message": "Invalid API key or malformed request"}
        )
    
    # Validate language
    valid_languages = ["Tamil", "English", "Hindi", "Malayalam", "Telugu"]
    if request.language not in valid_languages:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": f"Invalid language. Must be one of: {', '.join(valid_languages)}"}
        )
    
    # Validate audio format
    if request.audioFormat.lower() != "mp3":
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Only MP3 format is supported"}
        )
    
    try:
        # Decode base64 audio
        audio_data = base64.b64decode(request.audioBase64)
        
        # Analyze audio
        classification, confidence, explanation = analyze_audio_features(audio_data)
        
        # Store analysis in database (optional)
        analysis_record = {
            "id": str(uuid.uuid4()),
            "language": request.language,
            "classification": classification,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.voice_analyses.insert_one(analysis_record)
        
        return VoiceDetectionResponse(
            status="success",
            language=request.language,
            classification=classification,
            confidenceScore=confidence,
            explanation=explanation
        )
        
    except base64.binascii.Error:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Invalid base64 encoding"}
        )
    except Exception as e:
        logging.error(f"Voice detection error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Internal server error: {str(e)}"}
        )


@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "voice-detection-api"}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()