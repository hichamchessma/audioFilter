package com.audiofilter.service;

import com.audiofilter.model.AudioFile;
import com.audiofilter.model.ProcessingStatus;
import com.audiofilter.repository.AudioFileRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
@RequiredArgsConstructor
public class PythonProcessingService {
    private final RestTemplate restTemplate;
    private final AudioFileRepository audioFileRepository;

    @Value("${python-service.url}")
    private String pythonServiceUrl;

    @Async
    public void processAudioFileAsync(AudioFile audioFile) {
        try {
            audioFile.setStatus(ProcessingStatus.PROCESSING);
            audioFileRepository.save(audioFile);

            // Call Python service
            String processingEndpoint = pythonServiceUrl + "/process-audio";
            // Implementation of Python service call

            audioFile.setStatus(ProcessingStatus.COMPLETED);
        } catch (Exception e) {
            audioFile.setStatus(ProcessingStatus.FAILED);
        } finally {
            audioFileRepository.save(audioFile);
        }
    }
}
