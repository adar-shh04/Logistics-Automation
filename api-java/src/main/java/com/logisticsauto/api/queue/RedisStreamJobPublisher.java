package com.logisticsauto.api.queue;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.connection.stream.StreamRecords;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class RedisStreamJobPublisher implements JobPublisher {

    private static final Logger log = LoggerFactory.getLogger(RedisStreamJobPublisher.class);
    private final StringRedisTemplate redisTemplate;

    public RedisStreamJobPublisher(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @Override
    public void publish(String streamKey, Map<String, String> payload) {
        log.info("Publishing job to stream {}: job_id={}, document_id={}",
                streamKey, payload.get("job_id"), payload.get("document_id"));
        MapRecord<String, String, String> record = StreamRecords.mapBacked(payload).withStreamKey(streamKey);
        redisTemplate.opsForStream().add(record);
    }
}
