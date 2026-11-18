package com.logisticsauto.api.service;

import com.logisticsauto.api.web.exception.BadRequestException;
import org.springframework.web.multipart.MultipartFile;

import java.util.UUID;

public final class StorageValidationUtils {

    private StorageValidationUtils() {}

    public static String validateAndGenerateUid(MultipartFile file) {
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

        return UUID.randomUUID().toString().replace("-", "") + ext;
    }
}
