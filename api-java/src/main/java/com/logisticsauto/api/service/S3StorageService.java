package com.logisticsauto.api.service;

import com.logisticsauto.api.config.AppProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.S3ClientBuilder;
import software.amazon.awssdk.services.s3.S3Configuration;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;

import java.io.IOException;
import java.net.URI;

@Service
@ConditionalOnProperty(name = "app.storage.type", havingValue = "s3", matchIfMissing = true)
public class S3StorageService implements StorageService {

    private static final Logger log = LoggerFactory.getLogger(S3StorageService.class);

    private final AppProperties appProperties;
    private final S3Client s3Client;

    @Autowired
    public S3StorageService(AppProperties appProperties) {
        this.appProperties = appProperties;
        this.s3Client = buildS3Client(appProperties.storage() != null ? appProperties.storage().s3() : null);
    }

    public S3StorageService(AppProperties appProperties, S3Client s3Client) {
        this.appProperties = appProperties;
        this.s3Client = s3Client;
    }

    private static S3Client buildS3Client(AppProperties.S3 s3Props) {
        String regionStr = (s3Props != null && s3Props.region() != null && !s3Props.region().isBlank())
                ? s3Props.region()
                : "ap-south-1";

        S3ClientBuilder builder = S3Client.builder()
                .httpClient(UrlConnectionHttpClient.create())
                .region(Region.of(regionStr));

        if (s3Props != null) {
            if (s3Props.endpoint() != null && !s3Props.endpoint().isBlank()) {
                builder.endpointOverride(URI.create(s3Props.endpoint()));
            }

            if (s3Props.pathStyleAccess()) {
                builder.serviceConfiguration(S3Configuration.builder()
                        .pathStyleAccessEnabled(true)
                        .build());
            }

            if (s3Props.accessKey() != null && !s3Props.accessKey().isBlank()
                    && s3Props.secretKey() != null && !s3Props.secretKey().isBlank()) {
                builder.credentialsProvider(StaticCredentialsProvider.create(
                        AwsBasicCredentials.create(s3Props.accessKey(), s3Props.secretKey())
                ));
            } else {
                builder.credentialsProvider(DefaultCredentialsProvider.create());
            }
        } else {
            builder.credentialsProvider(DefaultCredentialsProvider.create());
        }

        return builder.build();
    }

    @Override
    public StoredFile save(MultipartFile file) {
        String uid = StorageValidationUtils.validateAndGenerateUid(file);
        String originalFilename = file.getOriginalFilename();
        String contentType = file.getContentType() != null ? file.getContentType() : "image/png";

        String bucket = (appProperties.storage() != null && appProperties.storage().s3() != null
                && appProperties.storage().s3().bucket() != null)
                ? appProperties.storage().s3().bucket()
                : "logistics-uploads";

        String objectKey = "uploads/" + uid;

        try {
            PutObjectRequest putReq = PutObjectRequest.builder()
                    .bucket(bucket)
                    .key(objectKey)
                    .contentType(contentType)
                    .build();

            s3Client.putObject(putReq, RequestBody.fromInputStream(file.getInputStream(), file.getSize()));
            log.info("Uploaded object to S3: s3://{}/{}", bucket, objectKey);

            String storageUri = String.format("s3://%s/%s", bucket, objectKey);
            return new StoredFile(uid, "", storageUri, originalFilename);
        } catch (IOException e) {
            throw new RuntimeException("Failed to upload file to S3", e);
        }
    }
}
