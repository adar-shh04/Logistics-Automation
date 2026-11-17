package com.logisticsauto.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app")
public record AppProperties(
        String uploadDir,
        String jobsStream
) {}
