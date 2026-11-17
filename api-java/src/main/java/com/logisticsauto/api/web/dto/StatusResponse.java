package com.logisticsauto.api.web.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record StatusResponse(
        String status,
        @JsonProperty("document_id") Integer documentId,
        @JsonProperty("transaction_id") Integer transactionId,
        @JsonProperty("invoice_number") String invoiceNumber,
        @JsonProperty("total_amount") String totalAmount,
        String gstin,
        String party,
        @JsonProperty("risk_score") BigDecimal riskScore,
        @JsonProperty("is_flagged") Boolean isFlagged,
        String message
) {
    public static StatusResponse processing() {
        return new StatusResponse("processing", null, null, null, null, null, null, null, null, null);
    }

    public static StatusResponse failed(String message) {
        return new StatusResponse("failed", null, null, null, null, null, null, null, null, message);
    }

    public static StatusResponse completed(
            Integer documentId,
            Integer transactionId,
            String invoiceNumber,
            String totalAmount,
            String gstin,
            String party,
            BigDecimal riskScore,
            Boolean isFlagged,
            String message
    ) {
        return new StatusResponse(
                "completed",
                documentId,
                transactionId,
                invoiceNumber,
                totalAmount,
                gstin,
                party,
                riskScore,
                isFlagged,
                message
        );
    }
}
