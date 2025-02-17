package com.audiofilter.controller;

import com.audiofilter.dto.AudioFileDTO;
import com.audiofilter.dto.ProcessedTrackDTO;
import com.audiofilter.model.AudioFile;
import com.audiofilter.model.ProcessedTrack;
import com.audiofilter.service.AudioProcessingService;
import com.audiofilter.service.StorageService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/audio")
@RequiredArgsConstructor
public class AudioController {
    private final AudioProcessingService audioProcessingService;
    private final StorageService storageService;

    @PostMapping("/upload")
    public ResponseEntity<AudioFileDTO> uploadFile(@RequestParam("file") MultipartFile file) throws IOException {
        AudioFile audioFile = audioProcessingService.uploadAudioFile(file);
        return ResponseEntity.ok(convertToDTO(audioFile));
    }

    @GetMapping("/{id}")
    public ResponseEntity<AudioFileDTO> getAudioFile(@PathVariable Long id) {
        AudioFile audioFile = audioProcessingService.getAudioFile(id);
        return ResponseEntity.ok(convertToDTO(audioFile));
    }

    @GetMapping("/{id}/tracks")
    public ResponseEntity<List<ProcessedTrackDTO>> getProcessedTracks(@PathVariable Long id) {
        List<ProcessedTrack> tracks = audioProcessingService.getProcessedTracks(id);
        List<ProcessedTrackDTO> trackDTOs = tracks.stream()
            .map(this::convertToDTO)
            .collect(Collectors.toList());
        return ResponseEntity.ok(trackDTOs);
    }

    @GetMapping
    public ResponseEntity<List<AudioFileDTO>> getAllAudioFiles() {
        List<AudioFile> audioFiles = audioProcessingService.getAllAudioFiles();
        List<AudioFileDTO> audioDTOs = audioFiles.stream()
            .map(this::convertToDTO)
            .collect(Collectors.toList());
        return ResponseEntity.ok(audioDTOs);
    }

    private AudioFileDTO convertToDTO(AudioFile audioFile) {
        AudioFileDTO dto = new AudioFileDTO();
        dto.setId(audioFile.getId());
        dto.setOriginalFileName(audioFile.getOriginalFileName());
        dto.setContentType(audioFile.getContentType());
        dto.setFileSize(audioFile.getFileSize());
        dto.setUploadedAt(audioFile.getUploadedAt());
        dto.setStatus(audioFile.getStatus());
        return dto;
    }

    private ProcessedTrackDTO convertToDTO(ProcessedTrack track) {
        ProcessedTrackDTO dto = new ProcessedTrackDTO();
        dto.setId(track.getId());
        dto.setAudioFileId(track.getAudioFile().getId());
        dto.setInstrumentType(track.getInstrumentType());
        dto.setProcessedAt(track.getProcessedAt());
        dto.setDownloadUrl(storageService.getPresignedUrl(track.getStorageKey()));
        return dto;
    }
}
