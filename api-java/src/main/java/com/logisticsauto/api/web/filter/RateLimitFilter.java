package com.logisticsauto.api.web.filter;

import com.logisticsauto.api.config.SecurityProperties;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class RateLimitFilter extends OncePerRequestFilter {

    private final SecurityProperties securityProperties;
    private final Map<String, Deque<Long>> clientRequestLog = new ConcurrentHashMap<>();

    public RateLimitFilter(SecurityProperties securityProperties) {
        this.securityProperties = securityProperties;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        if (!securityProperties.rateLimitEnabled()) {
            return true;
        }

        // Only rate limit POST /upload
        String path = request.getRequestURI();
        String method = request.getMethod();
        return !("POST".equalsIgnoreCase(method) && path.equals("/upload"));
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        String clientIp = getClientIp(request);
        long now = System.currentTimeMillis();
        long oneMinuteAgo = now - 60_000L;
        int maxAllowed = securityProperties.uploadRateLimitPerMinute();

        Deque<Long> timestamps = clientRequestLog.computeIfAbsent(clientIp, k -> new ArrayDeque<>());

        synchronized (timestamps) {
            // Evict entries older than 60 seconds
            while (!timestamps.isEmpty() && timestamps.peekFirst() < oneMinuteAgo) {
                timestamps.pollFirst();
            }

            if (timestamps.size() >= maxAllowed) {
                response.setStatus(429); // 429 Too Many Requests
                response.setContentType("application/json");
                response.setCharacterEncoding("UTF-8");
                response.getWriter().write(String.format(
                        "{\"error\":\"Too Many Requests\",\"message\":\"Upload rate limit exceeded (maximum %d per minute)\"}",
                        maxAllowed
                ));
                return;
            }

            timestamps.addLast(now);
        }

        filterChain.doFilter(request, response);
    }

    private String getClientIp(HttpServletRequest request) {
        String xf = request.getHeader("X-Forwarded-For");
        if (xf != null && !xf.isBlank()) {
            return xf.split(",")[0].trim();
        }
        return request.getRemoteAddr() != null ? request.getRemoteAddr() : "unknown";
    }
}
