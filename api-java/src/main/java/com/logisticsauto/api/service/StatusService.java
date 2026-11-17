package com.logisticsauto.api.service;

import com.logisticsauto.api.domain.Document;
import com.logisticsauto.api.domain.Transaction;
import com.logisticsauto.api.repo.DocumentRepository;
import com.logisticsauto.api.repo.TransactionRepository;
import com.logisticsauto.api.web.dto.StatusResponse;
import com.logisticsauto.api.web.exception.NotFoundException;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

@Service
public class StatusService {

    private final DocumentRepository documentRepository;
    private final TransactionRepository transactionRepository;

    public StatusService(DocumentRepository documentRepository, TransactionRepository transactionRepository) {
        this.documentRepository = documentRepository;
        this.transactionRepository = transactionRepository;
    }

    public StatusResponse getStatus(String uid) {
        Document doc = documentRepository.findByFilename(uid)
                .orElseThrow(() -> new NotFoundException("Document not found"));

        if ("failed".equalsIgnoreCase(doc.getStatus())) {
            String note = doc.getProcessingNotes();
            return StatusResponse.failed(note != null && !note.isBlank() ? note : "Processing failed");
        }

        if (!Boolean.TRUE.equals(doc.getProcessed())) {
            return StatusResponse.processing();
        }

        Optional<Transaction> txOpt = transactionRepository.findFirstByDocumentId(doc.getId());
        if (txOpt.isEmpty()) {
            return StatusResponse.processing();
        }

        Transaction tx = txOpt.get();
        Map<String, Object> fields = doc.getFields() != null ? doc.getFields() : Map.of();

        String invoiceNumber = getStringField(fields, "invoice_no");
        String totalAmount = formatAmount(fields.get("total_amount"));
        String gstin = getStringField(fields, "gstin");
        String party = getStringField(fields, "party");
        BigDecimal riskScore = formatRiskScore(tx.getRiskScore());
        Boolean isFlagged = Boolean.TRUE.equals(tx.getIsFlagged());
        String message = formatRiskMessage(isFlagged);

        return StatusResponse.completed(
                doc.getId(),
                tx.getId(),
                invoiceNumber,
                totalAmount,
                gstin,
                party,
                riskScore,
                isFlagged,
                message
        );
    }

    public String formatAmount(Object amountObj) {
        double amount = 0.0;
        if (amountObj instanceof Number num) {
            amount = num.doubleValue();
        } else if (amountObj instanceof String str && !str.isBlank()) {
            try {
                amount = Double.parseDouble(str.replace(",", "").trim());
            } catch (NumberFormatException ignored) {
                amount = 0.0;
            }
        }
        return String.format(Locale.US, "₹%,.2f", amount);
    }

    public BigDecimal formatRiskScore(Double riskScore) {
        if (riskScore == null) {
            return BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
        }
        return BigDecimal.valueOf(riskScore)
                .multiply(BigDecimal.valueOf(100))
                .setScale(2, RoundingMode.HALF_UP);
    }

    public String formatRiskMessage(Boolean isFlagged) {
        return Boolean.TRUE.equals(isFlagged) ? "⚠️ High Risk Transaction" : "✅ Safe Transaction";
    }

    private String getStringField(Map<String, Object> fields, String key) {
        Object val = fields.get(key);
        if (val == null) {
            return "N/A";
        }
        String s = String.valueOf(val).trim();
        return s.isEmpty() ? "N/A" : s;
    }
}
