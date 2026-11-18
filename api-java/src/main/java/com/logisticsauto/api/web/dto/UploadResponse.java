package com.logisticsauto.api.web.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record UploadResponse(
        String message,
        @JsonProperty("document_id") String documentId,
        String status
) {}
