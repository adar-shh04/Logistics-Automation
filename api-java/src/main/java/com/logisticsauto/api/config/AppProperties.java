package com.logisticsauto.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app")
public record AppProperties(
        String uploadDir,
        String jobsStream,
        Storage storage
) {
    public record Storage(
            String type,
            S3 s3
    ) {}

    public record S3(
            String bucket,
            String region,
            String endpoint,
            boolean pathStyleAccess,
            String accessKey,
            String secretKey
    ) {}
}
