package com.audiofilter.service;

import com.audiofilter.model.AudioFile;
import com.audiofilter.model.ProcessedTrack;
import com.audiofilter.model.ProcessingStatus;
import com.audiofilter.repository.AudioFileRepository;
import com.audiofilter.repository.ProcessedTrackRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import java.io.IOException;
import java.util.List;

@Service
@RequiredArgsConstructor
public class AudioProcessingService {
    private final AudioFileRepository audioFileRepository;
    private final ProcessedTrackRepository processedTrackRepository;
    private final StorageService storageService;
    private final PythonProcessingService pythonProcessingService;

    public AudioFile uploadAudioFile(MultipartFile file) throws IOException {
        // Create new audio file entity
        AudioFile audioFile = new AudioFile();
        audioFile.setOriginalFileName(file.getOriginalFilename());
        audioFile.setContentType(file.getContentType());
        audioFile.setFileSize(file.getSize());
        audioFile.setStatus(ProcessingStatus.PENDING);

        // Upload to storage
        String storageKey = storageService.uploadFile(file);
        audioFile.setStorageKey(storageKey);

        // Save to database
        audioFile = audioFileRepository.save(audioFile);

        // Trigger async processing
        pythonProcessingService.processAudioFileAsync(audioFile);

        return audioFile;
    }

    public List<ProcessedTrack> getProcessedTracks(Long audioFileId) {
        return processedTrackRepository.findByAudioFileId(audioFileId);
    }

    public AudioFile getAudioFile(Long id) {
        return audioFileRepository.findById(id)
            .orElseThrow(() -> new RuntimeException("Audio file not found"));
    }

    public List<AudioFile> getAllAudioFiles() {
        return audioFileRepository.findAll();
    }
}
