package com.audiofilter.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ProcessedTrackDTO {
    private Long id;
    private Long audioFileId;
    private String instrumentType;
    private String downloadUrl;
    private LocalDateTime processedAt;
}
