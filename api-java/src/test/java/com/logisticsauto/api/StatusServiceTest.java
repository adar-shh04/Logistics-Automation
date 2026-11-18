package com.logisticsauto.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.logisticsauto.api.repo.DocumentRepository;
import com.logisticsauto.api.repo.TransactionRepository;
import com.logisticsauto.api.service.StatusService;
import com.logisticsauto.api.web.dto.StatusResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

class StatusServiceTest {

    private StatusService statusService;
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        DocumentRepository documentRepository = Mockito.mock(DocumentRepository.class);
        TransactionRepository transactionRepository = Mockito.mock(TransactionRepository.class);
        statusService = new StatusService(documentRepository, transactionRepository);
        objectMapper = new ObjectMapper();
    }

    @Test
    void testFormatAmount() {
        assertThat(statusService.formatAmount(12345)).isEqualTo("₹12,345.00");
        assertThat(statusService.formatAmount(12345.0)).isEqualTo("₹12,345.00");
        assertThat(statusService.formatAmount(null)).isEqualTo("₹0.00");
        assertThat(statusService.formatAmount("")).isEqualTo("₹0.00");
        assertThat(statusService.formatAmount("abc")).isEqualTo("₹0.00");
    }

    @Test
    void testFormatRiskScore() {
        assertThat(statusService.formatRiskScore(0.63267)).isEqualByComparingTo(new BigDecimal("63.27"));
    }

    @Test
    void testFormatRiskMessage() {
        assertThat(statusService.formatRiskMessage(true)).isEqualTo("⚠️ High Risk Transaction");
        assertThat(statusService.formatRiskMessage(false)).isEqualTo("✅ Safe Transaction");
    }

    @Test
    void testProcessingResponseSerializesToExactJson() throws Exception {
        StatusResponse response = StatusResponse.processing();
        String json = objectMapper.writeValueAsString(response);
        assertThat(json).isEqualTo("{\"status\":\"processing\"}");
    }
}
