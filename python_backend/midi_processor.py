import os
import mido
from typing import Dict, List, Optional
import logging
import pretty_midi
import soundfile as sf
import numpy as np

logger = logging.getLogger(__name__)

class MidiProcessor:
    def __init__(self):
        self.supported_extensions = ['.mid', '.midi']

    def is_midi_file(self, file_path: str) -> bool:
        """Check if the file is a MIDI file based on extension."""
        return any(file_path.lower().endswith(ext) for ext in self.supported_extensions)

    def process_midi(self, input_path: str, output_dir: str) -> Dict[str, str]:
        """
        Process a MIDI file and extract information about tracks.
        
        Args:
            input_path: Path to the input MIDI file
            output_dir: Directory to save processed data
            
        Returns:
            Dictionary containing processed track information and paths
        """
        try:
            # Load MIDI file
            midi_data = pretty_midi.PrettyMIDI(input_path)
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Process each instrument
            track_info = {}
            for i, instrument in enumerate(midi_data.instruments):
                track_name = instrument.name if instrument.name else f"Track_{i}"
                
                # Get note pitches, ensuring they're converted to native Python types
                notes = instrument.notes
                pitches = [int(note.pitch) for note in notes] if notes else [0]
                
                # Count notes and other events
                track_info[track_name] = {
                    'program': int(instrument.program),
                    'is_drum': bool(instrument.is_drum),
                    'note_count': len(instrument.notes),
                    'pitch_range': [
                        int(min(pitches)),
                        int(max(pitches))
                    ]
                }
            
            # Synthesize audio
            audio_data = midi_data.synthesize(fs=44100)
            
            # Save as WAV file
            output_wav = os.path.join(output_dir, "output.wav")
            sf.write(output_wav, audio_data, 44100)
            
            result = {
                'tracks': track_info,
                'audio_file': output_wav
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error synthesizing audio: {str(e)}")
            raise

    def get_track_names(self, midi_path: str) -> List[str]:
        """Get a list of track names from a MIDI file."""
        try:
            midi_data = pretty_midi.PrettyMIDI(midi_path)
            return [instr.name if instr.name else f"Track_{i}" 
                   for i, instr in enumerate(midi_data.instruments)]
        except Exception as e:
            logger.error(f"Error getting track names: {str(e)}")
            return []
