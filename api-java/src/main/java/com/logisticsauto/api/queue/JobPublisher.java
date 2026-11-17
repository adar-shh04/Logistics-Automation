package com.logisticsauto.api.queue;

import java.util.Map;

public interface JobPublisher {
    void publish(String streamKey, Map<String, String> payload);
}
