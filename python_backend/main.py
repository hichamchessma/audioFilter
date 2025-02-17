from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import librosa
import numpy as np
from spleeter.separator import Separator
import os
import tempfile
import soundfile as sf

app = FastAPI(title="Audio Processing API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Spleeter separator
separator = Separator('spleeter:4stems')

@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...)):
    """
    Process an audio file to separate instruments.
    Returns separated stems: vocals, drums, bass, and other.
    """
    try:
        # Create a temporary directory to store the files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            temp_audio_path = os.path.join(temp_dir, file.filename)
            with open(temp_audio_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Separate the audio using Spleeter
            separator.separate_to_file(temp_audio_path, temp_dir)
            
            # Process results and return paths
            separated_files = {}
            for stem in ['vocals', 'drums', 'bass', 'other']:
                stem_path = os.path.join(temp_dir, f"{os.path.splitext(file.filename)[0]}/{stem}.wav")
                if os.path.exists(stem_path):
                    # Here you would typically save to MinIO/S3 and return URLs
                    separated_files[stem] = f"processed/{os.path.splitext(file.filename)[0]}/{stem}.wav"
            
            return {"status": "success", "separated_stems": separated_files}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
