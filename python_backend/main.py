from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import librosa
import numpy as np
from spleeter.separator import Separator
import os
import tempfile
import soundfile as sf
import logging
import warnings
import shutil
import subprocess
import urllib.request
import zipfile
import tarfile
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings('ignore')

# Create pretrained_models directory if it doesn't exist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "pretrained_models")
CHECKPOINT_DIR = os.path.join(MODELS_DIR, "4stems")
os.makedirs(MODELS_DIR, exist_ok=True)

def download_file(url, filename):
    """Download a file with progress indication"""
    logger.info(f"Downloading {url} to {filename}")
    try:
        urllib.request.urlretrieve(url, filename)
        return True
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return False

# Check if model exists, if not download it
def ensure_model():
    checkpoint_path = os.path.join(CHECKPOINT_DIR, "model.data-00000-of-00001")
    if not os.path.exists(checkpoint_path):
        logger.info("Downloading Spleeter 4stems model...")
        model_url = "https://github.com/deezer/spleeter/releases/download/v1.4.0/4stems.tar.gz"
        temp_file = os.path.join(tempfile.gettempdir(), "4stems.tar.gz")
        
        try:
            # Download the model
            if not download_file(model_url, temp_file):
                raise Exception("Failed to download model file")
            
            logger.info("Model downloaded, extracting...")
            
            # Extract using tarfile module
            with tarfile.open(temp_file, 'r:gz') as tar:
                # Create the target directory if it doesn't exist
                os.makedirs(CHECKPOINT_DIR, exist_ok=True)
                
                # Extract all files to the checkpoint directory
                tar.extractall(path=CHECKPOINT_DIR)
            
            logger.info("Model extracted successfully")
            
            # Verify the model files exist
            required_files = [
                "model.data-00000-of-00001",
                "model.index",
                "model.meta"
            ]
            
            missing_files = [
                f for f in required_files
                if not os.path.exists(os.path.join(CHECKPOINT_DIR, f))
            ]
            
            if missing_files:
                raise Exception(f"Missing model files: {missing_files}")
            
            logger.info("Model files verified successfully")
            
        except Exception as e:
            logger.error(f"Error setting up model: {str(e)}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.info("Cleaned up temporary file")

# Call ensure_model before initializing separator
ensure_model()

# Get FFmpeg path
FFMPEG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "ffmpeg", "ffmpeg-7.1-essentials_build", "bin", "ffmpeg.exe"))
logger.info(f"Looking for FFmpeg at: {FFMPEG_PATH}")

if not os.path.exists(FFMPEG_PATH):
    raise RuntimeError(f"FFmpeg not found at {FFMPEG_PATH}")

# Test FFmpeg
try:
    result = subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("FFmpeg test failed")
    logger.info("FFmpeg test successful")
except Exception as e:
    logger.error(f"FFmpeg test failed: {str(e)}")
    raise

# Set FFmpeg path in environment
os.environ["PATH"] = os.path.dirname(FFMPEG_PATH) + os.pathsep + os.environ["PATH"]
os.environ["FFMPEG_BINARY"] = FFMPEG_PATH
logger.info(f"Set FFMPEG_BINARY to: {FFMPEG_PATH}")

app = FastAPI(title="Audio Processing API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Spleeter separator with two stems
separator = Separator('spleeter:4stems', multiprocess=False)

@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...)):
    logger.info("Received audio file: %s", file.filename)
    try:
        # Create output directory
        output_base_dir = os.path.join(os.path.dirname(__file__), "processed")
        os.makedirs(output_base_dir, exist_ok=True)
        
        # Create a unique subdirectory for this processing
        output_dir = os.path.join(output_base_dir, os.path.splitext(file.filename)[0])
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            temp_audio_path = os.path.join(temp_dir, file.filename)
            content = await file.read()
            
            with open(temp_audio_path, "wb") as buffer:
                buffer.write(content)
            logger.info("Saved audio file to temporary path: %s", temp_audio_path)
            
            # Convert input to WAV using FFmpeg
            try:
                wav_path = os.path.join(temp_dir, "input.wav")
                result = subprocess.run([
                    FFMPEG_PATH,
                    "-i", temp_audio_path,
                    "-ar", "44100",  # Set sample rate
                    "-ac", "2",      # Set channels
                    "-y",            # Overwrite output
                    wav_path
                ], capture_output=True, text=True, encoding='utf-8')
                
                if result.returncode != 0:
                    raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")
                logger.info("Successfully converted audio to WAV")
                
            except Exception as e:
                logger.error("Error converting audio: %s", str(e))
                raise HTTPException(status_code=500, detail=str(e))
            
            try:
                # Verify model exists before processing
                ensure_model()
                
                # Create output directory for Spleeter
                temp_output_dir = os.path.join(temp_dir, "output")
                os.makedirs(temp_output_dir, exist_ok=True)
                
                # Separate the audio using Spleeter
                separator.separate_to_file(wav_path, temp_output_dir)
                logger.info("Successfully separated audio")
                
                # Process results and return paths
                separated_files = {}
                for stem in ['vocals', 'drums', 'bass', 'other']:
                    stem_path = os.path.join(temp_output_dir, "input", f"{stem}.wav")
                    if os.path.exists(stem_path):
                        # Copy the file to the permanent output directory
                        target_path = os.path.join(output_dir, f"{stem}.wav")
                        shutil.copy2(stem_path, target_path)
                        separated_files[stem] = target_path
                
                return {"status": "success", "files": separated_files}
                
            except Exception as e:
                logger.error("Error in separation: %s", str(e))
                raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Error processing audio file: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
