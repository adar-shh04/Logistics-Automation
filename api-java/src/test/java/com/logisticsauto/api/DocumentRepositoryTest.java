package com.logisticsauto.api;

import com.logisticsauto.api.domain.Document;
import com.logisticsauto.api.repo.DocumentRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.time.OffsetDateTime;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Testcontainers
class DocumentRepositoryTest {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15");

    @Autowired
    private DocumentRepository documentRepository;

    @Test
    void testSaveAndFindDocumentWithFields() {
        Document doc = new Document();
        doc.setFilename("test-file-1.png");
        doc.setOriginalFilename("original.png");
        doc.setFields(Map.of("invoice_no", "INV-100", "total_amount", 1234.56));
        doc.setUploadedAt(OffsetDateTime.now());
        doc.setProcessed(false);
        doc.setStatus("processing");

        Document saved = documentRepository.save(doc);
        assertThat(saved.getId()).isNotNull();

        Optional<Document> found = documentRepository.findByFilename("test-file-1.png");
        assertThat(found).isPresent();
        assertThat(found.get().getFields()).containsEntry("invoice_no", "INV-100");
    }
}
