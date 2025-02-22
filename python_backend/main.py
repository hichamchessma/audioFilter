from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
from midi_processor import MidiProcessor
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings('ignore')

# Create pretrained_models directory if it doesn't exist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "pretrained_models")
CHECKPOINT_DIR = os.path.join(MODELS_DIR, "5stems")
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
        logger.info("Downloading Spleeter 5stems model...")
        model_url = "https://github.com/deezer/spleeter/releases/download/v1.4.0/5stems.tar.gz"
        temp_file = os.path.join(tempfile.gettempdir(), "5stems.tar.gz")
        
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

# Initialize Spleeter separator with five stems (vocals, drums, bass, piano, other)
separator = Separator('spleeter:5stems', multiprocess=False)

# Create and mount static file directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), "processed")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/processed", StaticFiles(directory=STATIC_DIR), name="processed")

class AudioProcessor:
    def __init__(self):
        self.separator = separator
        self.midi_processor = MidiProcessor()
        
    async def process_file(self, file_path: str, output_dir: str) -> Dict[str, Any]:
        """Process an audio or MIDI file."""
        try:
            # Get lowercase file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Check if it's a MIDI file using MidiProcessor's validation
            if self.midi_processor.is_midi_file(file_path):
                result = self.midi_processor.process_midi(file_path, output_dir)
                # Convert numpy.int32 to native Python int
                if isinstance(result, np.int32):
                    result = int(result)
                return {
                    'status': 'success',
                    'type': 'midi',
                    'analysis': result
                }
            
            # If not MIDI, check if it's a supported audio format
            if file_ext not in ['.wav', '.mp3', '.ogg']:
                raise ValueError('Unsupported file format. Please provide a WAV, MP3, OGG, or MIDI file.')
            
            # Check audio duration
            duration = librosa.get_duration(filename=file_path)
            if duration > 600:  # 10 minutes
                raise ValueError('Audio file too long. Maximum duration is 10 minutes.')
            
            # Create output directory
            output_base_dir = os.path.join(os.path.dirname(__file__), "processed")
            os.makedirs(output_base_dir, exist_ok=True)
            
            # Create a unique subdirectory for this processing
            output_dir = os.path.join(output_base_dir, output_dir)
            os.makedirs(output_dir, exist_ok=True)
            
            # Create a temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                # Convert input to WAV using FFmpeg
                try:
                    wav_path = os.path.join(temp_dir, "input.wav")
                    result = subprocess.run([
                        FFMPEG_PATH,
                        "-i", file_path,
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
                    
                    # Process audio in chunks if necessary
                    if duration > 300:  # 5 minutes
                        logger.info("Processing audio in chunks...")
                        # Split audio into 5-minute chunks
                        chunk_duration = 300
                        num_chunks = int(duration // chunk_duration) + 1
                        
                        for i in range(num_chunks):
                            start_time = i * chunk_duration
                            end_time = min((i + 1) * chunk_duration, duration)
                            
                            # Create chunk path
                            chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
                            
                            # Extract chunk using FFmpeg
                            subprocess.run([
                                FFMPEG_PATH,
                                "-i", wav_path,
                                "-ss", str(start_time),
                                "-t", str(end_time - start_time),
                                "-y",
                                chunk_path
                            ], check=True)
                            
                            # Process chunk
                            self.separator.separate_to_file(chunk_path, temp_output_dir)
                            
                            # Clean up chunk file
                            os.remove(chunk_path)
                    else:
                        # Process entire file
                        self.separator.separate_to_file(wav_path, temp_output_dir)
                    
                    logger.info("Successfully separated audio")
                    
                    # Process results and return paths
                    separated_files = {}
                    # Map piano to guitar in the output
                    stem_mapping = {'vocals': 'vocals', 'drums': 'drums', 'bass': 'bass', 'piano': 'guitar', 'other': 'other'}
                    
                    for original_stem, mapped_stem in stem_mapping.items():
                        stem_path = os.path.join(temp_output_dir, "input", f"{original_stem}.wav")
                        if os.path.exists(stem_path):
                            # Copy the file to the permanent output directory with the mapped name
                            target_path = os.path.join(output_dir, f"{mapped_stem}.wav")
                            shutil.copy2(stem_path, target_path)
                            separated_files[mapped_stem] = target_path
                    
                    return {
                        "status": "success", 
                        "type": "audio",
                        "files": separated_files
                    }
                    
                except Exception as e:
                    logger.error("Error in separation: %s", str(e))
                    raise HTTPException(status_code=500, detail=str(e))
                    
        except Exception as e:
            logger.error("Error processing file: %s", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...)):
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name

        logger.info(f"Received audio file: {file.filename}")
        
        # Initialize processor
        processor = AudioProcessor()
        
        # Create output directory using filename without extension
        filename = os.path.splitext(os.path.basename(file.filename))[0]
        output_dir = os.path.join("Results", filename)
        os.makedirs(output_dir, exist_ok=True)
        
        # Process audio file
        result = await processor.process_file(temp_file_path, output_dir)
        
        # Clean up temporary file
        os.remove(temp_file_path)
        
        # Convert file paths to URLs
        if result.get('type') == 'audio' and result.get('files'):
            base_url = "http://localhost:8000/processed"
            for stem, path in result['files'].items():
                relative_path = os.path.relpath(path, STATIC_DIR)
                result['files'][stem] = f"{base_url}/{relative_path.replace(os.sep, '/')}"
        
        return result
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
