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
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedFiles, setProcessedFiles] = useState({});
  const [activeFilters, setActiveFilters] = useState({
    vocals: true,
    drums: true,
    bass: true,
    guitar: true,
    other: true
  });

  const onDrop = useCallback(acceptedFiles => {
    setFile(acceptedFiles[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.flac', '.aac', '.mid'],
      'video/*': ['.mp4']
    }
  });

  const handleUpload = async () => {
    if (!file) return;

    setIsProcessing(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/process-audio', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (data.status === 'success' && data.files) {
        setProcessedFiles(data.files);
      }
    } catch (error) {
      console.error('Error uploading file:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const toggleFilter = (filterName) => {
    setActiveFilters(prev => ({
      ...prev,
      [filterName]: !prev[filterName]
    }));
  };

  const handleDownload = async (url, stemName) => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `${stemName}.wav`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Error downloading file:', error);
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

        {Object.keys(processedFiles).length > 0 && (
          <Box className="filters-container" sx={{ mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              Audio Filters
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              {Object.keys(activeFilters).map((filter) => (
                <Button
                  key={filter}
                  variant={activeFilters[filter] ? "contained" : "outlined"}
                  onClick={() => toggleFilter(filter)}
                  sx={{ textTransform: 'capitalize' }}
                >
                  {filter}
                </Button>
              ))}
            </Box>
            {Object.entries(processedFiles).map(([stem, path]) => (
              <Box 
                key={stem} 
                sx={{ 
                  mt: 2, 
                  display: activeFilters[stem] ? 'block' : 'none',
                  backgroundColor: '#f5f5f5',
                  padding: 2,
                  borderRadius: 1
                }}
              >
                <Box sx={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between',
                  mb: 1
                }}>
                  <Typography variant="subtitle1" sx={{ textTransform: 'capitalize' }}>
                    {stem}
                  </Typography>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => handleDownload(path, stem)}
                    startIcon={<CloudDownloadIcon />}
                  >
                    Download
                  </Button>
                </Box>
                <audio 
                  controls 
                  src={path} 
                  style={{ width: '100%' }} 
                  preload="metadata"
                />
              </Box>
            ))}
          </Box>
        )}
      </Paper>
    </Container>
  );
}

export default App;
