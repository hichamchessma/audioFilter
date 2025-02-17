package com.audiofilter.model;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "processed_tracks")
public class ProcessedTrack {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne
    @JoinColumn(name = "audio_file_id", nullable = false)
    private AudioFile audioFile;

    @Column(nullable = false)
    private String instrumentType;

    @Column(nullable = false)
    private String storageKey;

    @Column(nullable = false)
    private LocalDateTime processedAt;

    @PrePersist
    protected void onCreate() {
        processedAt = LocalDateTime.now();
    }
}
