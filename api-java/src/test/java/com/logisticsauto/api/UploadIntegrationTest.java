package com.logisticsauto.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.logisticsauto.api.config.AppProperties;
import com.logisticsauto.api.domain.Document;
import com.logisticsauto.api.repo.DocumentRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
class UploadIntegrationTest {

    @TempDir
    static Path tempDir;

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15");

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine").withExposedPorts(6379);

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.data.redis.host", redis::getHost);
        registry.add("spring.data.redis.port", redis::getFirstMappedPort);
        registry.add("app.upload-dir", () -> tempDir.toString());
        registry.add("app.storage.type", () -> "local");
    }

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private DocumentRepository documentRepository;

    @Autowired
    private StringRedisTemplate redisTemplate;

    @Autowired
    private AppProperties appProperties;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void testUploadIntegrationWorkflow() throws Exception {
        byte[] content = new byte[]{(byte) 0x89, 'P', 'N', 'G', 1, 2, 3};
        MockMultipartFile file = new MockMultipartFile(
                "file", "sample_invoice.png", "image/png", content
        );

        MvcResult result = mockMvc.perform(multipart("/upload").file(file))
                .andExpect(status().isOk())
                .andReturn();

        JsonNode responseNode = objectMapper.readTree(result.getResponse().getContentAsString());
        String uid = responseNode.get("document_id").asText();
        assertThat(uid).endsWith(".png");
        assertThat(responseNode.get("status").asText()).isEqualTo("processing");

        Optional<Document> docOpt = documentRepository.findByFilename(uid);
        assertThat(docOpt).isPresent();
        Document doc = docOpt.get();
        assertThat(doc.getOriginalFilename()).isEqualTo("sample_invoice.png");
        assertThat(doc.getStatus()).isEqualTo("processing");

        Path savedFile = tempDir.resolve(uid);
        assertThat(Files.exists(savedFile)).isTrue();
        assertThat(Files.readAllBytes(savedFile)).isEqualTo(content);

        List<MapRecord<String, Object, Object>> records =
                redisTemplate.opsForStream().range(appProperties.jobsStream(), org.springframework.data.domain.Range.unbounded());

        assertThat(records).isNotNull().hasSize(1);
        MapRecord<String, Object, Object> record = records.get(0);
        Map<Object, Object> valMap = record.getValue();

        assertThat(valMap.get("document_id")).isEqualTo(String.valueOf(doc.getId()));
        assertThat(valMap.get("file_path")).isEqualTo(savedFile.toString());
        assertThat(valMap.get("storage_uri")).isEqualTo("file://" + savedFile.toAbsolutePath().toString().replace("\\", "/"));
        assertThat(valMap.get("attempt")).isEqualTo("1");
        assertThat(valMap.get("job_id")).isNotNull();
        assertThat(valMap.get("enqueued_at")).isNotNull();
    }
}
