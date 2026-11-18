package com.logisticsauto.api;

import com.logisticsauto.api.config.AppProperties;
import com.logisticsauto.api.service.FileStorageService;
import com.logisticsauto.api.web.exception.BadRequestException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;

import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class FileStorageServiceTest {

    @TempDir
    Path tempDir;

    private FileStorageService fileStorageService;

    @BeforeEach
    void setUp() {
        AppProperties appProperties = new AppProperties(tempDir.toString(), "logistics:jobs");
        fileStorageService = new FileStorageService(appProperties);
    }

    @Test
    void testSaveJpegSuccess() {
        MockMultipartFile file = new MockMultipartFile(
                "file", "test.jpg", "image/jpeg", new byte[]{1, 2, 3, 4}
        );
        FileStorageService.StoredFile stored = fileStorageService.save(file);

        assertThat(stored.uid()).endsWith(".jpg");
        assertThat(stored.uid()).hasSize(36); // 32 hex + .jpg (4) = 36
        assertThat(stored.originalFilename()).isEqualTo("test.jpg");
        assertThat(Path.of(stored.filePath())).exists();
    }

    @Test
    void testSavePngSuccess() {
        MockMultipartFile file = new MockMultipartFile(
                "file", "test.png", "image/png", new byte[]{1, 2, 3, 4}
        );
        FileStorageService.StoredFile stored = fileStorageService.save(file);

        assertThat(stored.uid()).endsWith(".png");
        assertThat(stored.uid()).hasSize(36); // 32 hex + .png (4) = 36
        assertThat(Path.of(stored.filePath())).exists();
    }

    @Test
    void testSaveEmptyFileThrowsBadRequest() {
        MockMultipartFile file = new MockMultipartFile(
                "file", "empty.png", "image/png", new byte[0]
        );
        assertThatThrownBy(() -> fileStorageService.save(file))
                .isInstanceOf(BadRequestException.class)
                .hasMessage("File is empty");
    }

    @Test
    void testSavePdfThrowsBadRequest() {
        MockMultipartFile file = new MockMultipartFile(
                "file", "document.pdf", "application/pdf", new byte[]{1, 2, 3}
        );
        assertThatThrownBy(() -> fileStorageService.save(file))
                .isInstanceOf(BadRequestException.class)
                .hasMessage("Only JPEG or PNG images are supported");
    }

    @Test
    void testSavePathTraversalThrowsBadRequest() {
        MockMultipartFile file = new MockMultipartFile(
                "file", "../evil.png", "image/png", new byte[]{1, 2, 3}
        );
        assertThatThrownBy(() -> fileStorageService.save(file))
                .isInstanceOf(BadRequestException.class)
                .hasMessage("Invalid filename");
    }
}
