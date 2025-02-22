import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
  Box, 
  Container, 
  Typography, 
  Paper, 
  Button,
  LinearProgress,
  IconButton
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import AudioFileIcon from '@mui/icons-material/AudioFile';
import DeleteIcon from '@mui/icons-material/Delete';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const onDrop = useCallback(acceptedFiles => {
    setFile(acceptedFiles[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.flac', '.aac'],
      'video/*': ['.mp4']
    }
  });

  const handleUpload = async () => {
    if (!file) return;

    setIsProcessing(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      // Replace with your actual API endpoint
      const response = await fetch('http://localhost:8000/process-audio', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      console.log(data);
      // Handle success
    } catch (error) {
      console.error('Error uploading file:', error);
      // Handle error
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Container maxWidth="md" className="app-container">
      <Typography variant="h2" className="title">
        Audio Filter App
      </Typography>
      
      <Paper elevation={3} className="upload-container">
        <Box {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
          <input {...getInputProps()} />
          <CloudUploadIcon className="upload-icon" />
          {file ? (
            <Box className="file-info">
              <AudioFileIcon className="audio-icon" />
              <Typography variant="body1">{file.name}</Typography>
              <IconButton 
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
                className="delete-button"
              >
                <DeleteIcon />
              </IconButton>
            </Box>
          ) : (
            <Typography variant="h6">
              {isDragActive
                ? "Drop the audio file here"
                : "Drag & drop an audio file here, or click to select"}
            </Typography>
          )}
        </Box>

        {file && (
          <Box className="upload-actions">
            <Button
              variant="contained"
              color="primary"
              onClick={handleUpload}
              disabled={isProcessing}
              startIcon={<CloudUploadIcon />}
            >
              Process Audio
            </Button>
          </Box>
        )}

        {isProcessing && (
          <Box className="progress-container">
            <LinearProgress />
            <Typography variant="body2" color="textSecondary">
              Processing your audio file...
            </Typography>
          </Box>
        )}
      </Paper>
    </Container>
  );
}

export default App;
