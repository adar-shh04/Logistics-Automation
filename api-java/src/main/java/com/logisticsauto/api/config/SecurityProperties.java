package com.logisticsauto.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.security")
public record SecurityProperties(
        String apiKey,
        boolean rateLimitEnabled,
        int uploadRateLimitPerMinute
) {
    public SecurityProperties {
        apiKey = apiKey != null ? apiKey.trim() : "";
        if (uploadRateLimitPerMinute <= 0) {
            uploadRateLimitPerMinute = 10;
        }
    }
}
