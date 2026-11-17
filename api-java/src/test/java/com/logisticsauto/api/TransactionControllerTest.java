package com.logisticsauto.api;

import com.logisticsauto.api.domain.Transaction;
import com.logisticsauto.api.repo.TransactionRepository;
import com.logisticsauto.api.web.GlobalExceptionHandler;
import com.logisticsauto.api.web.TransactionController;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;
import java.util.Optional;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(TransactionController.class)
@Import(GlobalExceptionHandler.class)
class TransactionControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private TransactionRepository transactionRepository;

    @Test
    void testGetTransactionHappyPath() throws Exception {
        Transaction tx = new Transaction();
        tx.setId(7);
        tx.setDocumentId(12);
        tx.setInvoiceValue(12345.0);
        tx.setHsCode("8471");
        tx.setParty("ACME");
        tx.setRiskScore(0.6327);
        tx.setIsFlagged(true);
        tx.setMetadata(Map.of("key", "value"));

        when(transactionRepository.findById(7)).thenReturn(Optional.of(tx));

        mockMvc.perform(get("/transaction/7"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(7))
                .andExpect(jsonPath("$.invoice_value").value(12345.0))
                .andExpect(jsonPath("$.hs_code").value("8471"))
                .andExpect(jsonPath("$.party").value("ACME"))
                .andExpect(jsonPath("$.risk_score").value(0.6327))
                .andExpect(jsonPath("$.is_flagged").value(true))
                .andExpect(jsonPath("$.metadata.key").value("value"));
    }

    @Test
    void testGetTransactionNotFoundReturns404() throws Exception {
        when(transactionRepository.findById(999)).thenReturn(Optional.empty());

        mockMvc.perform(get("/transaction/999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.detail").value("Transaction not found"));
    }
}
