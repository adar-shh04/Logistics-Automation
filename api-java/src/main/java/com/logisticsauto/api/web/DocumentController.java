package com.logisticsauto.api.web;

import com.logisticsauto.api.service.StatusService;
import com.logisticsauto.api.service.UploadService;
import com.logisticsauto.api.web.dto.StatusResponse;
import com.logisticsauto.api.web.dto.UploadResponse;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
public class DocumentController {

    private final UploadService uploadService;
    private final StatusService statusService;

    public DocumentController(UploadService uploadService, StatusService statusService) {
        this.uploadService = uploadService;
        this.statusService = statusService;
    }

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<UploadResponse> upload(@RequestParam("file") MultipartFile file) {
        UploadResponse response = uploadService.upload(file);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/status/{uid}")
    public ResponseEntity<StatusResponse> getStatus(@PathVariable("uid") String uid) {
        StatusResponse response = statusService.getStatus(uid);
        return ResponseEntity.ok(response);
    }
}
