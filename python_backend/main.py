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

# Configure logging
logging.basicConfig(level=logging.INFO)

# Suppress warnings
warnings.filterwarnings('ignore')

# Get FFmpeg path
FFMPEG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "ffmpeg", "ffmpeg-7.1-essentials_build", "bin", "ffmpeg.exe"))
logging.info(f"Looking for FFmpeg at: {FFMPEG_PATH}")

if not os.path.exists(FFMPEG_PATH):
    raise RuntimeError(f"FFmpeg not found at {FFMPEG_PATH}")

# Test FFmpeg
try:
    result = subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("FFmpeg test failed")
    logging.info("FFmpeg test successful")
except Exception as e:
    logging.error(f"FFmpeg test failed: {str(e)}")
    raise

# Set FFmpeg path in environment
os.environ["PATH"] = os.path.dirname(FFMPEG_PATH) + os.pathsep + os.environ["PATH"]
os.environ["FFMPEG_BINARY"] = FFMPEG_PATH
logging.info(f"Set FFMPEG_BINARY to: {FFMPEG_PATH}")

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
    logging.info("Received audio file: %s", file.filename)
    try:
        # Create a temporary directory to store the files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            temp_audio_path = os.path.join(temp_dir, file.filename)
            content = await file.read()
            
            with open(temp_audio_path, "wb") as buffer:
                buffer.write(content)
            logging.info("Saved audio file to temporary path: %s", temp_audio_path)
            
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
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")
                logging.info("Successfully converted audio to WAV")
                
            except Exception as e:
                logging.error("Error converting audio: %s", str(e))
                raise HTTPException(status_code=500, detail="Error converting audio file")
            
            try:
                # Create output directory for Spleeter
                output_dir = os.path.join(temp_dir, "output")
                os.makedirs(output_dir, exist_ok=True)
                
                # Separate the audio using Spleeter
                separator.separate_to_file(wav_path, output_dir)
                logging.info("Successfully separated audio")
                
                # Process results and return paths
                separated_files = {}
                for stem in ['vocals', 'drums', 'bass', 'other']:
                    stem_path = os.path.join(output_dir, "input", f"{stem}.wav")
                    if os.path.exists(stem_path):
                        # Create processed directory if it doesn't exist
                        processed_dir = os.path.join(os.path.dirname(__file__), "processed", os.path.splitext(file.filename)[0])
                        os.makedirs(processed_dir, exist_ok=True)
                        
                        # Copy the stem file to the processed directory
                        target_path = os.path.join(processed_dir, f"{stem}.wav")
                        shutil.copy2(stem_path, target_path)
                        
                        separated_files[stem] = f"processed/{os.path.splitext(file.filename)[0]}/{stem}.wav"
                        logging.info("Found and copied separated stem: %s", stem)
                
                return {"status": "success", "separated_stems": separated_files}
            except Exception as e:
                logging.error("Error in separation: %s", str(e))
                raise HTTPException(status_code=500, detail="Error during audio separation")
    
    except Exception as e:
        logging.error("Error processing audio file: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
