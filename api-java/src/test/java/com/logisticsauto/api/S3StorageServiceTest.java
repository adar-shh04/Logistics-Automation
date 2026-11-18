package com.logisticsauto.api;

import com.logisticsauto.api.config.AppProperties;
import com.logisticsauto.api.service.S3StorageService;
import com.logisticsauto.api.service.StorageService;
import com.logisticsauto.api.web.exception.BadRequestException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.model.PutObjectResponse;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class S3StorageServiceTest {

    @Mock
    private S3Client s3Client;

    private S3StorageService s3StorageService;

    @BeforeEach
    void setUp() {
        AppProperties.S3 s3Props = new AppProperties.S3(
                "my-test-bucket",
                "ap-south-1",
                "http://localhost:4566",
                true,
                "test",
                "test"
        );
        AppProperties appProperties = new AppProperties(
                "/data/uploads",
                "logistics:jobs",
                new AppProperties.Storage("s3", s3Props)
        );
        s3StorageService = new S3StorageService(appProperties, s3Client);
    }

    @Test
    void testSaveS3PngSuccess() {
        when(s3Client.putObject(any(PutObjectRequest.class), any(RequestBody.class)))
                .thenReturn(PutObjectResponse.builder().build());

        MockMultipartFile file = new MockMultipartFile(
                "file", "invoice.png", "image/png", new byte[]{10, 20, 30}
        );

        StorageService.StoredFile stored = s3StorageService.save(file);

        assertThat(stored.uid()).endsWith(".png");
        assertThat(stored.uid()).hasSize(36);
        assertThat(stored.originalFilename()).isEqualTo("invoice.png");
        assertThat(stored.storageUri()).isEqualTo("s3://my-test-bucket/uploads/" + stored.uid());

        ArgumentCaptor<PutObjectRequest> reqCaptor = ArgumentCaptor.forClass(PutObjectRequest.class);
        verify(s3Client).putObject(reqCaptor.capture(), any(RequestBody.class));

        PutObjectRequest capturedReq = reqCaptor.getValue();
        assertThat(capturedReq.bucket()).isEqualTo("my-test-bucket");
        assertThat(capturedReq.key()).isEqualTo("uploads/" + stored.uid());
        assertThat(capturedReq.contentType()).isEqualTo("image/png");
    }

    @Test
    void testSaveS3RejectsPdf() {
        MockMultipartFile file = new MockMultipartFile(
                "file", "invoice.pdf", "application/pdf", new byte[]{1, 2, 3}
        );

        assertThatThrownBy(() -> s3StorageService.save(file))
                .isInstanceOf(BadRequestException.class)
                .hasMessage("Only JPEG or PNG images are supported");
    }
}
