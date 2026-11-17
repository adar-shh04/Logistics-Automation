package com.logisticsauto.api.web.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

public record TransactionResponse(
        Integer id,
        @JsonProperty("invoice_value") Double invoiceValue,
        @JsonProperty("hs_code") String hsCode,
        String party,
        @JsonProperty("risk_score") Double riskScore,
        @JsonProperty("is_flagged") Boolean isFlagged,
        Map<String, Object> metadata
) {}
