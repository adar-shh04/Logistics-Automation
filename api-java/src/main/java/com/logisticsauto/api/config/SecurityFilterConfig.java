package com.logisticsauto.api.config;

import com.logisticsauto.api.web.filter.ApiKeyAuthFilter;
import com.logisticsauto.api.web.filter.RateLimitFilter;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(SecurityProperties.class)
public class SecurityFilterConfig {

    @Bean
    public FilterRegistrationBean<ApiKeyAuthFilter> apiKeyAuthFilter(SecurityProperties securityProperties) {
        FilterRegistrationBean<ApiKeyAuthFilter> registration = new FilterRegistrationBean<>();
        registration.setFilter(new ApiKeyAuthFilter(securityProperties));
        registration.addUrlPatterns("/upload", "/status/*", "/transaction/*");
        registration.setOrder(1);
        return registration;
    }

    @Bean
    public FilterRegistrationBean<RateLimitFilter> rateLimitFilter(SecurityProperties securityProperties) {
        FilterRegistrationBean<RateLimitFilter> registration = new FilterRegistrationBean<>();
        registration.setFilter(new RateLimitFilter(securityProperties));
        registration.addUrlPatterns("/upload");
        registration.setOrder(2);
        return registration;
    }
}
