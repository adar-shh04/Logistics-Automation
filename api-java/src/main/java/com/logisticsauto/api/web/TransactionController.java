package com.logisticsauto.api.web;

import com.logisticsauto.api.domain.Transaction;
import com.logisticsauto.api.repo.TransactionRepository;
import com.logisticsauto.api.web.dto.TransactionResponse;
import com.logisticsauto.api.web.exception.NotFoundException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class TransactionController {

    private final TransactionRepository transactionRepository;

    public TransactionController(TransactionRepository transactionRepository) {
        this.transactionRepository = transactionRepository;
    }

    @GetMapping("/transaction/{id}")
    public ResponseEntity<TransactionResponse> getTransaction(@PathVariable("id") Integer id) {
        Transaction tx = transactionRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("Transaction not found"));

        Map<String, Object> metadata = tx.getMetadata() != null ? tx.getMetadata() : Map.of();

        TransactionResponse response = new TransactionResponse(
                tx.getId(),
                tx.getInvoiceValue(),
                tx.getHsCode(),
                tx.getParty(),
                tx.getRiskScore(),
                tx.getIsFlagged(),
                metadata
        );

        return ResponseEntity.ok(response);
    }
}
