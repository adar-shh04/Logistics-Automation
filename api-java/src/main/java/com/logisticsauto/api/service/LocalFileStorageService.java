package com.logisticsauto.api.service;

import com.logisticsauto.api.config.AppProperties;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;

@Service
@ConditionalOnProperty(name = "app.storage.type", havingValue = "local")
public class LocalFileStorageService implements StorageService {

    private final AppProperties appProperties;

    public LocalFileStorageService(AppProperties appProperties) {
        this.appProperties = appProperties;
    }

    @Override
    public StoredFile save(MultipartFile file) {
        String uid = StorageValidationUtils.validateAndGenerateUid(file);
        String originalFilename = file.getOriginalFilename();

        try {
            Path dir = Paths.get(appProperties.uploadDir() != null ? appProperties.uploadDir() : "/data/uploads");
            Files.createDirectories(dir);
            Path target = dir.resolve(uid);
            Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);
            String storageUri = "file://" + target.toAbsolutePath().toString().replace("\\", "/");
            return new StoredFile(uid, target.toString(), storageUri, originalFilename);
        } catch (IOException e) {
            throw new RuntimeException("Failed to store uploaded file locally", e);
        }
    }
}
