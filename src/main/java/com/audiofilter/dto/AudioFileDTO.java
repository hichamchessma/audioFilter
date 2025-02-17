package com.audiofilter.dto;

import com.audiofilter.model.ProcessingStatus;
import lombok.Data;
import java.time.LocalDateTime;

@Data
public class AudioFileDTO {
    private Long id;
    private String originalFileName;
    private String contentType;
    private Long fileSize;
    private LocalDateTime uploadedAt;
    private ProcessingStatus status;
}
