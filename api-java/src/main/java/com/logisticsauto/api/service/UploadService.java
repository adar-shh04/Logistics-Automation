package com.logisticsauto.api.service;

import com.logisticsauto.api.config.AppProperties;
import com.logisticsauto.api.domain.Document;
import com.logisticsauto.api.queue.JobPublisher;
import com.logisticsauto.api.repo.DocumentRepository;
import com.logisticsauto.api.web.dto.UploadResponse;
import com.logisticsauto.api.web.exception.BadRequestException;
import com.logisticsauto.api.web.exception.QueueUnavailableException;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
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

    private final StorageService storageService;
    private final DocumentRepository documentRepository;
    private final JobPublisher jobPublisher;
    private final AppProperties appProperties;

    private final Counter acceptedUploads;
    private final Counter rejectedUploads;
    private final Counter queueFailedUploads;
    private final Timer jobPublishTimer;

    public UploadService(
            StorageService storageService,
            DocumentRepository documentRepository,
            JobPublisher jobPublisher,
            AppProperties appProperties,
            MeterRegistry meterRegistry
    ) {
        this.storageService = storageService;
        this.documentRepository = documentRepository;
        this.jobPublisher = jobPublisher;
        this.appProperties = appProperties;

        this.acceptedUploads = Counter.builder("logistics_uploads_total")
                .tag("outcome", "accepted")
                .description("Total document upload attempts")
                .register(meterRegistry);

        this.rejectedUploads = Counter.builder("logistics_uploads_total")
                .tag("outcome", "rejected")
                .description("Total document upload attempts")
                .register(meterRegistry);

        this.queueFailedUploads = Counter.builder("logistics_uploads_total")
                .tag("outcome", "queue_failed")
                .description("Total document upload attempts")
                .register(meterRegistry);

        this.jobPublishTimer = Timer.builder("logistics_job_publish_seconds")
                .description("Time taken to publish jobs to Redis stream")
                .register(meterRegistry);
    }

    public UploadResponse upload(MultipartFile file) {
        StorageService.StoredFile storedFile;
        try {
            storedFile = storageService.save(file);
        } catch (BadRequestException e) {
            rejectedUploads.increment();
            throw e;
        } catch (Exception e) {
            rejectedUploads.increment();
            throw e;
        }

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
                    "file_path", storedFile.filePath() != null ? storedFile.filePath() : "",
                    "storage_uri", storedFile.storageUri() != null ? storedFile.storageUri() : "",
                    "attempt", "1",
                    "enqueued_at", Instant.now().toString()
            );
            jobPublishTimer.record(() -> jobPublisher.publish(appProperties.jobsStream(), payload));
        } catch (Exception e) {
            log.error("Failed to publish job to Redis stream: {}", e.getMessage(), e);
            doc.setStatus("failed");
            doc.setProcessingNotes("Queue unavailable");
            documentRepository.save(doc);
            queueFailedUploads.increment();
            throw new QueueUnavailableException("Queue unavailable");
        }

        acceptedUploads.increment();
        return new UploadResponse(
                "Document uploaded successfully",
                storedFile.uid(),
                "processing"
        );
    }
}
