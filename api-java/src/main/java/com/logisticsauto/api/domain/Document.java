package com.logisticsauto.api.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;
import java.util.Map;

@Entity
@Table(name = "documents")
public class Document {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "filename", nullable = false)
    private String filename;

    @Column(name = "original_filename")
    private String originalFilename;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "fields", columnDefinition = "json")
    private Map<String, Object> fields;

    @Column(name = "uploaded_at")
    private OffsetDateTime uploadedAt;

    @Column(name = "processed")
    private Boolean processed = false;

    @Column(name = "processing_notes")
    private String processingNotes;

    @Column(name = "status", nullable = false)
    private String status = "processing";

    public Document() {
    }

    public Document(String filename, String originalFilename) {
        this.filename = filename;
        this.originalFilename = originalFilename;
        this.uploadedAt = OffsetDateTime.now();
        this.processed = false;
        this.status = "processing";
    }

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public String getFilename() {
        return filename;
    }

    public void setFilename(String filename) {
        this.filename = filename;
    }

    public String getOriginalFilename() {
        return originalFilename;
    }

    public void setOriginalFilename(String originalFilename) {
        this.originalFilename = originalFilename;
    }

    public Map<String, Object> getFields() {
        return fields;
    }

    public void setFields(Map<String, Object> fields) {
        this.fields = fields;
    }

    public OffsetDateTime getUploadedAt() {
        return uploadedAt;
    }

    public void setUploadedAt(OffsetDateTime uploadedAt) {
        this.uploadedAt = uploadedAt;
    }

    public Boolean getProcessed() {
        return processed;
    }

    public void setProcessed(Boolean processed) {
        this.processed = processed;
    }

    public String getProcessingNotes() {
        return processingNotes;
    }

    public void setProcessingNotes(String processingNotes) {
        this.processingNotes = processingNotes;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
