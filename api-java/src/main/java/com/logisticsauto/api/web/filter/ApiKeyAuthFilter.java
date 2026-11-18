package com.logisticsauto.api.web.filter;

import com.logisticsauto.api.config.SecurityProperties;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

public class ApiKeyAuthFilter extends OncePerRequestFilter {

    public static final String API_KEY_HEADER = "X-API-KEY";

    private final SecurityProperties securityProperties;

    public ApiKeyAuthFilter(SecurityProperties securityProperties) {
        this.securityProperties = securityProperties;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        // If no API key is configured, allow all requests (local dev / loadtest mode)
        if (securityProperties.apiKey() == null || securityProperties.apiKey().isBlank()) {
            return true;
        }

        String path = request.getRequestURI();
        // Public endpoints
        if (path.equals("/health") || path.startsWith("/actuator") || path.startsWith("/error")) {
            return true;
        }

        // Only enforce for /upload, /status, /transaction
        boolean isProtected = path.equals("/upload")
                || path.startsWith("/status")
                || path.startsWith("/transaction");

        return !isProtected;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        String configuredKey = securityProperties.apiKey();
        String headerKey = request.getHeader(API_KEY_HEADER);

        // Also check Authorization header fallback (e.g. "Bearer <key>" or "ApiKey <key>")
        if (headerKey == null || headerKey.isBlank()) {
            String authHeader = request.getHeader("Authorization");
            if (authHeader != null && authHeader.startsWith("Bearer ")) {
                headerKey = authHeader.substring(7).trim();
            } else if (authHeader != null && authHeader.startsWith("ApiKey ")) {
                headerKey = authHeader.substring(7).trim();
            }
        }

        if (headerKey == null || !headerKey.equals(configuredKey)) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json");
            response.setCharacterEncoding("UTF-8");
            response.getWriter().write("{\"error\":\"Unauthorized\",\"message\":\"Invalid or missing API key\"}");
            return;
        }

        filterChain.doFilter(request, response);
    }
}
