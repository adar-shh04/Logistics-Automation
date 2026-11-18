package com.logisticsauto.api;

import com.logisticsauto.api.service.StatusService;
import com.logisticsauto.api.service.UploadService;
import com.logisticsauto.api.web.DocumentController;
import com.logisticsauto.api.web.GlobalExceptionHandler;
import com.logisticsauto.api.web.dto.StatusResponse;
import com.logisticsauto.api.web.dto.UploadResponse;
import com.logisticsauto.api.web.exception.BadRequestException;
import com.logisticsauto.api.web.exception.NotFoundException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(DocumentController.class)
@Import(GlobalExceptionHandler.class)
class DocumentControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private UploadService uploadService;

    @MockitoBean
    private StatusService statusService;

    @Test
    void testUploadHappyPath() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file", "invoice.png", "image/png", new byte[]{1, 2, 3}
        );
        when(uploadService.upload(any())).thenReturn(
                new UploadResponse("Document uploaded successfully", "1234567890abcdef1234567890abcdef.png", "processing")
        );

        mockMvc.perform(multipart("/upload").file(file))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Document uploaded successfully"))
                .andExpect(jsonPath("$.document_id").value("1234567890abcdef1234567890abcdef.png"))
                .andExpect(jsonPath("$.status").value("processing"));
    }

    @Test
    void testUploadEmptyFileReturns400() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file", "empty.png", "image/png", new byte[0]
        );
        when(uploadService.upload(any())).thenThrow(new BadRequestException("File is empty"));

        mockMvc.perform(multipart("/upload").file(file))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("File is empty"));
    }

    @Test
    void testUploadTxtFileReturns400() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file", "test.txt", "text/plain", "hello".getBytes()
        );
        when(uploadService.upload(any())).thenThrow(new BadRequestException("Only JPEG or PNG images are supported"));

        mockMvc.perform(multipart("/upload").file(file))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("Only JPEG or PNG images are supported"));
    }

    @Test
    void testGetStatusHappyPath() throws Exception {
        when(statusService.getStatus("doc123")).thenReturn(StatusResponse.processing());

        mockMvc.perform(get("/status/doc123"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("processing"));
    }

    @Test
    void testGetStatusNotFoundReturns404() throws Exception {
        when(statusService.getStatus("missing")).thenThrow(new NotFoundException("Document not found"));

        mockMvc.perform(get("/status/missing"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.detail").value("Document not found"));
    }
}
