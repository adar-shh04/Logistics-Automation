package com.logisticsauto.api.web.exception;

public class QueueUnavailableException extends RuntimeException {
    public QueueUnavailableException(String message) {
        super(message);
    }
}
