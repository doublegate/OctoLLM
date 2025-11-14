//! Prometheus metrics for the Reflex Layer
//!
//! Provides comprehensive metrics for monitoring performance, detection rates,
//! cache efficiency, and rate limiting.

use lazy_static::lazy_static;
use prometheus::{
    register_histogram_vec, register_int_counter, register_int_counter_vec, HistogramVec,
    IntCounter, IntCounterVec,
};

lazy_static! {
    /// Total HTTP requests by method and path
    pub static ref REQUEST_COUNT: IntCounterVec = register_int_counter_vec!(
        "reflex_http_requests_total",
        "Total number of HTTP requests by method and path",
        &["method", "path"]
    )
    .unwrap();

    /// HTTP request duration by method, path, and status
    pub static ref REQUEST_DURATION: HistogramVec = register_histogram_vec!(
        "reflex_http_request_duration_seconds",
        "HTTP request duration in seconds",
        &["method", "path", "status"],
        vec![0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    .unwrap();

    /// PII detection duration
    pub static ref PII_DETECTION_DURATION: HistogramVec = register_histogram_vec!(
        "reflex_pii_detection_duration_seconds",
        "Time spent on PII detection",
        &["pattern_set"],
        vec![0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1]
    )
    .unwrap();

    /// Total PII detections
    pub static ref PII_DETECTIONS: IntCounterVec = register_int_counter_vec!(
        "reflex_pii_detections_total",
        "Total number of PII detections by type",
        &["pii_type"]
    )
    .unwrap();

    /// Injection detection duration
    pub static ref INJECTION_DETECTION_DURATION: HistogramVec = register_histogram_vec!(
        "reflex_injection_detection_duration_seconds",
        "Time spent on injection detection",
        &["detection_mode"],
        vec![0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1]
    )
    .unwrap();

    /// Total injection detections by severity
    pub static ref INJECTION_DETECTIONS: IntCounterVec = register_int_counter_vec!(
        "reflex_injection_detections_total",
        "Total number of injection detections by severity",
        &["severity"]
    )
    .unwrap();

    /// Cache hits
    pub static ref CACHE_HITS: IntCounter = register_int_counter!(
        "reflex_cache_hits_total",
        "Total number of cache hits"
    )
    .unwrap();

    /// Cache misses
    pub static ref CACHE_MISSES: IntCounter = register_int_counter!(
        "reflex_cache_misses_total",
        "Total number of cache misses"
    )
    .unwrap();

    /// Cache operation duration
    pub static ref CACHE_OPERATION_DURATION: HistogramVec = register_histogram_vec!(
        "reflex_cache_operation_duration_seconds",
        "Time spent on cache operations",
        &["operation"],
        vec![0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1]
    )
    .unwrap();

    /// Rate limit checks allowed
    pub static ref RATE_LIMIT_ALLOWED: IntCounter = register_int_counter!(
        "reflex_rate_limit_allowed_total",
        "Total number of rate limit checks that passed"
    )
    .unwrap();

    /// Rate limit checks rejected by dimension (ip, user, endpoint, global)
    pub static ref RATE_LIMIT_REJECTED: IntCounterVec = register_int_counter_vec!(
        "reflex_rate_limit_rejected_total",
        "Total number of rate limit checks that were rejected",
        &["dimension"]
    )
    .unwrap();

    /// Rate limit operation duration
    pub static ref RATE_LIMIT_DURATION: HistogramVec = register_histogram_vec!(
        "reflex_rate_limit_duration_seconds",
        "Time spent on rate limit checks",
        &["dimension"],
        vec![0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1]
    )
    .unwrap();

    /// Requests blocked due to critical injection
    pub static ref REQUESTS_BLOCKED: IntCounter = register_int_counter!(
        "reflex_requests_blocked_total",
        "Total number of requests blocked due to critical injection"
    )
    .unwrap();
}

/// Register custom metrics for specific operations
// NOTE: These functions will be used in Sprint 1.2 HTTP handler implementation
#[allow(dead_code)]
pub fn record_pii_detection(duration_secs: f64, pattern_set: &str) {
    PII_DETECTION_DURATION
        .with_label_values(&[pattern_set])
        .observe(duration_secs);
}

#[allow(dead_code)]
pub fn record_pii_match(pii_type: &str) {
    PII_DETECTIONS.with_label_values(&[pii_type]).inc();
}

#[allow(dead_code)]
pub fn record_injection_detection(duration_secs: f64, detection_mode: &str) {
    INJECTION_DETECTION_DURATION
        .with_label_values(&[detection_mode])
        .observe(duration_secs);
}

#[allow(dead_code)]
pub fn record_injection_match(severity: &str) {
    INJECTION_DETECTIONS.with_label_values(&[severity]).inc();
}

#[allow(dead_code)]
pub fn record_cache_hit() {
    CACHE_HITS.inc();
}

#[allow(dead_code)]
pub fn record_cache_miss() {
    CACHE_MISSES.inc();
}

#[allow(dead_code)]
pub fn record_cache_operation(operation: &str, duration_secs: f64) {
    CACHE_OPERATION_DURATION
        .with_label_values(&[operation])
        .observe(duration_secs);
}

#[allow(dead_code)]
pub fn record_rate_limit_allowed() {
    RATE_LIMIT_ALLOWED.inc();
}

#[allow(dead_code)]
pub fn record_rate_limit_rejected(dimension: &str) {
    RATE_LIMIT_REJECTED.with_label_values(&[dimension]).inc();
}

#[allow(dead_code)]
pub fn record_rate_limit_check(dimension: &str, duration_secs: f64) {
    RATE_LIMIT_DURATION
        .with_label_values(&[dimension])
        .observe(duration_secs);
}

#[allow(dead_code)]
pub fn record_request_blocked() {
    REQUESTS_BLOCKED.inc();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metrics_registration() {
        // Just ensure all metrics are properly registered
        assert_eq!(REQUEST_COUNT.with_label_values(&["GET", "/"]).get(), 0);
        assert_eq!(CACHE_HITS.get(), 0);
        assert_eq!(RATE_LIMIT_ALLOWED.get(), 0);
    }

    #[test]
    fn test_record_functions() {
        record_pii_detection(0.001, "standard");
        record_pii_match("email");
        record_injection_detection(0.002, "standard");
        record_injection_match("critical");
        record_cache_hit();
        record_cache_miss();
        record_cache_operation("get", 0.0005);
        record_rate_limit_allowed();
        record_rate_limit_rejected("ip");
        record_rate_limit_check("ip", 0.0003);
        record_request_blocked();

        // Verify counts incremented
        assert!(CACHE_HITS.get() > 0);
        assert!(CACHE_MISSES.get() > 0);
        assert!(RATE_LIMIT_ALLOWED.get() > 0);
        assert!(REQUESTS_BLOCKED.get() > 0);
    }
}
