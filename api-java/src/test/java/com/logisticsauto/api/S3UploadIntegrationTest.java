package com.logisticsauto.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.logisticsauto.api.config.AppProperties;
import com.logisticsauto.api.domain.Document;
import com.logisticsauto.api.repo.DocumentRepository;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
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
import org.testcontainers.containers.localstack.LocalStackContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.CreateBucketRequest;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
class S3UploadIntegrationTest {

    private static final String BUCKET_NAME = "logistics-test-bucket";

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15");

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine").withExposedPorts(6379);

    @Container
    static LocalStackContainer localstack = new LocalStackContainer(DockerImageName.parse("localstack/localstack:3.0"))
            .withServices(LocalStackContainer.Service.S3);

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.data.redis.host", redis::getHost);
        registry.add("spring.data.redis.port", redis::getFirstMappedPort);
        registry.add("app.storage.type", () -> "s3");
        registry.add("app.storage.s3.bucket", () -> BUCKET_NAME);
        registry.add("app.storage.s3.region", localstack::getRegion);
        registry.add("app.storage.s3.endpoint", () -> localstack.getEndpointOverride(LocalStackContainer.Service.S3).toString());
        registry.add("app.storage.s3.path-style-access", () -> true);
        registry.add("app.storage.s3.access-key", localstack::getAccessKey);
        registry.add("app.storage.s3.secret-key", localstack::getSecretKey);
    }

    @BeforeAll
    static void initBucket() {
        S3Client s3 = S3Client.builder()
                .httpClient(UrlConnectionHttpClient.create())
                .endpointOverride(localstack.getEndpointOverride(LocalStackContainer.Service.S3))
                .credentialsProvider(StaticCredentialsProvider.create(
                        AwsBasicCredentials.create(localstack.getAccessKey(), localstack.getSecretKey())
                ))
                .region(Region.of(localstack.getRegion()))
                .build();
        s3.createBucket(CreateBucketRequest.builder().bucket(BUCKET_NAME).build());
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
    void testUploadS3IntegrationWorkflow() throws Exception {
        byte[] content = new byte[]{(byte) 0x89, 'P', 'N', 'G', 99, 88, 77};
        MockMultipartFile file = new MockMultipartFile(
                "file", "cloud_invoice.png", "image/png", content
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
        assertThat(doc.getOriginalFilename()).isEqualTo("cloud_invoice.png");

        List<MapRecord<String, Object, Object>> records =
                redisTemplate.opsForStream().range(appProperties.jobsStream(), org.springframework.data.domain.Range.unbounded());

        assertThat(records).isNotNull().hasSize(1);
        MapRecord<String, Object, Object> record = records.get(0);
        Map<Object, Object> valMap = record.getValue();

        assertThat(valMap.get("document_id")).isEqualTo(String.valueOf(doc.getId()));
        assertThat(valMap.get("storage_uri")).isEqualTo("s3://" + BUCKET_NAME + "/uploads/" + uid);

        // Verify the object is actually in S3
        S3Client s3 = S3Client.builder()
                .httpClient(UrlConnectionHttpClient.create())
                .endpointOverride(localstack.getEndpointOverride(LocalStackContainer.Service.S3))
                .credentialsProvider(StaticCredentialsProvider.create(
                        AwsBasicCredentials.create(localstack.getAccessKey(), localstack.getSecretKey())
                ))
                .region(Region.of(localstack.getRegion()))
                .build();

        byte[] fetched = s3.getObject(GetObjectRequest.builder().bucket(BUCKET_NAME).key("uploads/" + uid).build()).readAllBytes();
        assertThat(fetched).isEqualTo(content);
    }
}
