import pytest
from fastapi.testclient import TestClient
from main import app
import os
import tempfile
import numpy as np
import soundfile as sf

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_process_audio_invalid_file(client):
    response = client.post("/process-audio", files={"file": ("test.txt", "invalid content")})
    assert response.status_code == 500

def test_process_audio(client):
    # Create a simple test audio file
    test_audio_path = "test_audio.wav"
    try:
        # Generate a simple sine wave
        sample_rate = 44100
        duration = 2  # seconds
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
        
        # Ensure audio data is float32 and normalized
        audio_data = audio_data.astype(np.float32)
        audio_data = audio_data / np.max(np.abs(audio_data))
        
        # Save the test audio file
        sf.write(test_audio_path, audio_data, sample_rate, format='WAV', subtype='FLOAT')
        
        # Test the endpoint
        with open(test_audio_path, "rb") as audio_file:
            response = client.post(
                "/process-audio",
                files={"file": ("test.wav", audio_file, "audio/wav")}
            )
        
        assert response.status_code == 200
        result = response.json()
        assert "status" in result
        assert result["status"] == "success"
        assert "separated_stems" in result
        
        # Check if all expected stems are present
        expected_stems = ['vocals', 'drums', 'bass', 'other']
        stems = result["separated_stems"]
        for stem in expected_stems:
            assert stem in stems
    
    finally:
        # Clean up the test file
        if os.path.exists(test_audio_path):
            os.remove(test_audio_path)
