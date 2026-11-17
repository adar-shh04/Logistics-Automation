package com.logisticsauto.api.service;

import com.logisticsauto.api.config.AppProperties;
import com.logisticsauto.api.web.exception.BadRequestException;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.UUID;

@Service
public class FileStorageService {

    private final AppProperties appProperties;

    public FileStorageService(AppProperties appProperties) {
        this.appProperties = appProperties;
    }

    public record StoredFile(String uid, String filePath, String originalFilename) {}

    public StoredFile save(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new BadRequestException("File is empty");
        }

        String contentType = file.getContentType();
        boolean validContentType = contentType != null && (
                contentType.equalsIgnoreCase("image/jpeg") ||
                contentType.equalsIgnoreCase("image/png") ||
                contentType.equalsIgnoreCase("image/jpg")
        );
        if (!validContentType) {
            throw new BadRequestException("Only JPEG or PNG images are supported");
        }

        String originalFilename = file.getOriginalFilename();
        if (originalFilename != null && (
                originalFilename.contains("..") ||
                originalFilename.contains("/") ||
                originalFilename.contains("\\")
        )) {
            throw new BadRequestException("Invalid filename");
        }

        String ext = ".png";
        if (originalFilename != null && originalFilename.lastIndexOf('.') != -1) {
            String candidateExt = originalFilename.substring(originalFilename.lastIndexOf('.'));
            if (!candidateExt.matches("^\\.[a-zA-Z0-9]+$")) {
                throw new BadRequestException("Invalid file extension");
            }
            ext = candidateExt.toLowerCase();
        }

        String uid = UUID.randomUUID().toString().replace("-", "") + ext;

        try {
            Path dir = Paths.get(appProperties.uploadDir());
            Files.createDirectories(dir);
            Path target = dir.resolve(uid);
            Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);
            return new StoredFile(uid, target.toString(), originalFilename);
        } catch (IOException e) {
            throw new RuntimeException("Failed to store uploaded file", e);
        }
    }
}
