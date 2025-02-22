import os
import mido
from typing import Dict, List, Optional
import logging

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
            midi_file = mido.MidiFile(input_path)
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Process each track
            track_info = {}
            for i, track in enumerate(midi_file.tracks):
                track_name = track.name if hasattr(track, 'name') and track.name else f"Track_{i}"
                
                # Count messages by type
                message_counts = {}
                for msg in track:
                    msg_type = msg.type
                    message_counts[msg_type] = message_counts.get(msg_type, 0) + 1
                
                # Save track information
                track_info[track_name] = {
                    'message_counts': message_counts,
                    'length': len(track),
                    'ticks': sum(msg.time for msg in track if hasattr(msg, 'time'))
                }
            
            # Save analysis results
            output_path = os.path.join(output_dir, "midi_analysis.txt")
            with open(output_path, 'w') as f:
                f.write(f"MIDI File Analysis: {os.path.basename(input_path)}\n")
                f.write(f"Format: {midi_file.type}\n")
                f.write(f"Number of tracks: {len(midi_file.tracks)}\n")
                f.write(f"Ticks per beat: {midi_file.ticks_per_beat}\n\n")
                
                for track_name, info in track_info.items():
                    f.write(f"\nTrack: {track_name}\n")
                    f.write(f"Length: {info['length']} messages\n")
                    f.write(f"Total ticks: {info['ticks']}\n")
                    f.write("Message types:\n")
                    for msg_type, count in info['message_counts'].items():
                        f.write(f"  - {msg_type}: {count}\n")
            
            return {
                'analysis_path': output_path,
                'track_info': track_info
            }
            
        except Exception as e:
            logger.error(f"Error processing MIDI file: {str(e)}")
            raise

    def get_track_names(self, midi_path: str) -> List[str]:
        """Get a list of track names from a MIDI file."""
        try:
            midi_file = mido.MidiFile(midi_path)
            track_names = []
            
            for i, track in enumerate(midi_file.tracks):
                name = track.name if hasattr(track, 'name') and track.name else f"Track_{i}"
                track_names.append(name)
                
            return track_names
        except Exception as e:
            logger.error(f"Error getting track names: {str(e)}")
            raise
