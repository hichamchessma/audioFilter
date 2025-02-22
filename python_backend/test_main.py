import pytest
from fastapi.testclient import TestClient
from main import app
import os
import tempfile
import numpy as np
import soundfile as sf
from midi_processor import MidiProcessor
import mido
import shutil

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_process_audio_invalid_file():
    """Test processing an invalid audio file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create an invalid file
        test_file_path = os.path.join(temp_dir, "test.txt")
        with open(test_file_path, "w") as f:
            f.write("This is not an audio file")
        
        # Try to process the invalid file
        with TestClient(app) as client:
            with open(test_file_path, "rb") as test_file:
                response = client.post(
                    "/process-audio",
                    files={"file": ("test.txt", test_file, "text/plain")}
                )
            
            assert response.status_code == 500

def test_process_audio():
    """Test audio file processing functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a simple test audio file
        test_audio_path = os.path.join(temp_dir, "test_audio.wav")
        
        # Generate a simple sine wave
        sample_rate = 44100
        duration = 2  # seconds
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
        
        # Normalize audio
        audio_data = audio_data.astype(np.float32)
        audio_data = audio_data / np.max(np.abs(audio_data))
        
        # Save the audio file
        sf.write(test_audio_path, audio_data, sample_rate)
        
        # Create test client and process the audio
        with TestClient(app) as client:
            with open(test_audio_path, "rb") as audio_file:
                response = client.post(
                    "/process-audio",
                    files={"file": ("test.wav", audio_file, "audio/wav")}
                )
            
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            assert result["type"] == "audio"
            assert "files" in result
            
            # Check if all expected stems are present
            expected_stems = ['vocals', 'drums', 'bass', 'other']
            for stem in expected_stems:
                assert stem in result["files"]

def test_midi_processing():
    """Test MIDI file processing functionality."""
    # Create a test MIDI file in a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        test_midi_path = os.path.join(temp_dir, "test.mid")
        midi_file = mido.MidiFile()
        track = mido.MidiTrack()
        track.name = "Test Track"
        
        # Add messages
        track.append(mido.MetaMessage('track_name', name='Test Track', time=0))
        track.append(mido.Message('note_on', note=60, velocity=64, time=0))
        track.append(mido.Message('note_off', note=60, velocity=64, time=480))
        track.append(mido.MetaMessage('end_of_track', time=0))
        midi_file.tracks.append(track)
        midi_file.save(test_midi_path)

        # Process the MIDI file
        processor = MidiProcessor()
        output_dir = os.path.join(temp_dir, "test_output")
        result = processor.process_midi(test_midi_path, output_dir)

        # Verify the results
        assert 'analysis_path' in result
        assert os.path.exists(result['analysis_path'])
        assert 'track_info' in result
        assert 'Test Track' in result['track_info']
        assert result['track_info']['Test Track']['length'] == 5  # Including all metadata messages
