package com.audiofilter.repository;

import com.audiofilter.model.ProcessedTrack;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface ProcessedTrackRepository extends JpaRepository<ProcessedTrack, Long> {
    List<ProcessedTrack> findByAudioFileId(Long audioFileId);
}
