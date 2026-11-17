package com.logisticsauto.api.service;

import com.logisticsauto.api.config.AppProperties;
import com.logisticsauto.api.domain.Document;
import com.logisticsauto.api.queue.JobPublisher;
import com.logisticsauto.api.repo.DocumentRepository;
import com.logisticsauto.api.web.dto.UploadResponse;
import com.logisticsauto.api.web.exception.QueueUnavailableException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Service
public class UploadService {

    private static final Logger log = LoggerFactory.getLogger(UploadService.class);

    private final FileStorageService fileStorageService;
    private final DocumentRepository documentRepository;
    private final JobPublisher jobPublisher;
    private final AppProperties appProperties;

    public UploadService(
            FileStorageService fileStorageService,
            DocumentRepository documentRepository,
            JobPublisher jobPublisher,
            AppProperties appProperties
    ) {
        this.fileStorageService = fileStorageService;
        this.documentRepository = documentRepository;
        this.jobPublisher = jobPublisher;
        this.appProperties = appProperties;
    }

    public UploadResponse upload(MultipartFile file) {
        FileStorageService.StoredFile storedFile = fileStorageService.save(file);

        Document doc = new Document();
        doc.setFilename(storedFile.uid());
        doc.setOriginalFilename(storedFile.originalFilename());
        doc.setFields(new HashMap<>());
        doc.setProcessed(false);
        doc.setStatus("processing");
        doc.setUploadedAt(OffsetDateTime.now());

        doc = documentRepository.save(doc);

        try {
            String jobId = UUID.randomUUID().toString();
            Map<String, String> payload = Map.of(
                    "job_id", jobId,
                    "document_id", String.valueOf(doc.getId()),
                    "file_path", storedFile.filePath(),
                    "attempt", "1",
                    "enqueued_at", Instant.now().toString()
            );
            jobPublisher.publish(appProperties.jobsStream(), payload);
        } catch (Exception e) {
            log.error("Failed to publish job to Redis stream: {}", e.getMessage(), e);
            doc.setStatus("failed");
            doc.setProcessingNotes("Queue unavailable");
            documentRepository.save(doc);
            throw new QueueUnavailableException("Queue unavailable");
        }

        return new UploadResponse(
                "Document uploaded successfully",
                storedFile.uid(),
                "processing"
        );
    }
}
