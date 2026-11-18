package com.logisticsauto.api;

import com.logisticsauto.api.config.SecurityProperties;
import com.logisticsauto.api.web.filter.ApiKeyAuthFilter;
import com.logisticsauto.api.web.filter.RateLimitFilter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.io.IOException;

import static org.assertj.core.api.Assertions.assertThat;

class SecurityFilterTest {

    @Test
    void testApiKeyDisabledPassesThrough() throws ServletException, IOException {
        SecurityProperties props = new SecurityProperties("", false, 10);
        ApiKeyAuthFilter filter = new ApiKeyAuthFilter(props);

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/upload");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);
        assertThat(response.getStatus()).isEqualTo(200);
    }

    @Test
    void testApiKeyRequiredBlocksMissingKey() throws ServletException, IOException {
        SecurityProperties props = new SecurityProperties("my-secret-key", false, 10);
        ApiKeyAuthFilter filter = new ApiKeyAuthFilter(props);

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/upload");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);
        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(response.getContentAsString()).contains("Unauthorized");
    }

    @Test
    void testApiKeyRequiredAllowsValidHeader() throws ServletException, IOException {
        SecurityProperties props = new SecurityProperties("my-secret-key", false, 10);
        ApiKeyAuthFilter filter = new ApiKeyAuthFilter(props);

        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/upload");
        request.addHeader("X-API-KEY", "my-secret-key");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);
        assertThat(response.getStatus()).isEqualTo(200);
    }

    @Test
    void testApiKeyAllowsPublicHealthEndpoint() throws ServletException, IOException {
        SecurityProperties props = new SecurityProperties("my-secret-key", false, 10);
        ApiKeyAuthFilter filter = new ApiKeyAuthFilter(props);

        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/health");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);
        assertThat(response.getStatus()).isEqualTo(200);
    }

    @Test
    void testRateLimitBlocksExcessiveRequests() throws ServletException, IOException {
        SecurityProperties props = new SecurityProperties("", true, 2);
        RateLimitFilter filter = new RateLimitFilter(props);

        MockHttpServletRequest req1 = new MockHttpServletRequest("POST", "/upload");
        req1.setRemoteAddr("192.168.1.50");
        MockHttpServletResponse res1 = new MockHttpServletResponse();
        filter.doFilter(req1, res1, new MockFilterChain());
        assertThat(res1.getStatus()).isEqualTo(200);

        MockHttpServletRequest req2 = new MockHttpServletRequest("POST", "/upload");
        req2.setRemoteAddr("192.168.1.50");
        MockHttpServletResponse res2 = new MockHttpServletResponse();
        filter.doFilter(req2, res2, new MockFilterChain());
        assertThat(res2.getStatus()).isEqualTo(200);

        // Third request exceeds limit of 2
        MockHttpServletRequest req3 = new MockHttpServletRequest("POST", "/upload");
        req3.setRemoteAddr("192.168.1.50");
        MockHttpServletResponse res3 = new MockHttpServletResponse();
        filter.doFilter(req3, res3, new MockFilterChain());
        assertThat(res3.getStatus()).isEqualTo(429);
        assertThat(res3.getContentAsString()).contains("Too Many Requests");
    }
}
