package com.logisticsauto.api.service;

import org.springframework.web.multipart.MultipartFile;

public interface StorageService {

    record StoredFile(String uid, String filePath, String storageUri, String originalFilename) {}

    StoredFile save(MultipartFile file);
}
