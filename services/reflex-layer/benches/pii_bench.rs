// PII Detection Performance Benchmarks
//
// This benchmark suite validates that PII detection meets the <5ms P95 latency target.

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion};
use reflex_layer::{redact, PIIConfig, PIIDetector, PIIType, PatternSet, RedactionStrategy};

/// Benchmark individual pattern detection
fn bench_individual_patterns(c: &mut Criterion) {
    let detector = PIIDetector::new(PIIConfig {
        pattern_set: PatternSet::Standard,
        enable_validation: false,
        enable_context: false,
    });

    let mut group = c.benchmark_group("individual_patterns");

    // SSN detection
    group.bench_function("ssn", |b| {
        b.iter(|| detector.detect(black_box("My SSN is 123-45-6789 for verification.")))
    });

    // Email detection
    group.bench_function("email", |b| {
        b.iter(|| detector.detect(black_box("Contact me at user@example.com for details.")))
    });

    // Credit card detection
    group.bench_function("credit_card", |b| {
        b.iter(|| detector.detect(black_box("Card: 4532-1234-5678-9010 expires soon.")))
    });

    // Phone detection
    group.bench_function("phone", |b| {
        b.iter(|| detector.detect(black_box("Call me at (555) 123-4567 anytime.")))
    });

    // IPv4 detection
    group.bench_function("ipv4", |b| {
        b.iter(|| detector.detect(black_box("Server at 192.168.1.100 is responding.")))
    });

    group.finish();
}

/// Benchmark detection with validation enabled
fn bench_with_validation(c: &mut Criterion) {
    let mut group = c.benchmark_group("validation");

    // Without validation
    let detector_no_validation = PIIDetector::new(PIIConfig {
        pattern_set: PatternSet::Standard,
        enable_validation: false,
        enable_context: false,
    });

    group.bench_function("without_validation", |b| {
        b.iter(|| {
            detector_no_validation.detect(black_box("SSN: 123-45-6789, Card: 4532-1234-5678-9010"))
        })
    });

    // With validation
    let detector_with_validation = PIIDetector::new(PIIConfig {
        pattern_set: PatternSet::Standard,
        enable_validation: true,
        enable_context: false,
    });

    group.bench_function("with_validation", |b| {
        b.iter(|| {
            detector_with_validation
                .detect(black_box("SSN: 123-45-6789, Card: 4532-1234-5678-9010"))
        })
    });

    group.finish();
}

/// Benchmark different pattern sets
fn bench_pattern_sets(c: &mut Criterion) {
    let text = "Email: test@example.com, SSN: 123-45-6789, IP: 192.168.1.1, MAC: 00:11:22:33:44:55";

    let mut group = c.benchmark_group("pattern_sets");

    // Strict mode (fewer patterns)
    let strict_detector = PIIDetector::new(PIIConfig {
        pattern_set: PatternSet::Strict,
        enable_validation: false,
        enable_context: false,
    });

    group.bench_function("strict", |b| {
        b.iter(|| strict_detector.detect(black_box(text)))
    });

    // Standard mode
    let standard_detector = PIIDetector::new(PIIConfig {
        pattern_set: PatternSet::Standard,
        enable_validation: false,
        enable_context: false,
    });

    group.bench_function("standard", |b| {
        b.iter(|| standard_detector.detect(black_box(text)))
    });

    // Relaxed mode (all patterns)
    let relaxed_detector = PIIDetector::new(PIIConfig {
        pattern_set: PatternSet::Relaxed,
        enable_validation: false,
        enable_context: false,
    });

    group.bench_function("relaxed", |b| {
        b.iter(|| relaxed_detector.detect(black_box(text)))
    });

    group.finish();
}

/// Benchmark different text sizes
fn bench_text_sizes(c: &mut Criterion) {
    let detector = PIIDetector::new(PIIConfig {
        pattern_set: PatternSet::Standard,
        enable_validation: false,
        enable_context: false,
    });

    let mut group = c.benchmark_group("text_sizes");

    // Small text (100 bytes)
    let small_text = "Email: test@example.com, Phone: 555-123-4567";
    group.bench_function(BenchmarkId::new("small", small_text.len()), |b| {
        b.iter(|| detector.detect(black_box(small_text)))
    });

    // Medium text (1KB)
    let medium_text = format!(
        "User profile: email is test@example.com, phone is 555-123-4567. {}",
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. ".repeat(15)
    );
    group.bench_function(BenchmarkId::new("medium", medium_text.len()), |b| {
        b.iter(|| detector.detect(black_box(&medium_text)))
    });

    // Large text (10KB)
    let large_text = format!(
        "Document with PII: email test@example.com, SSN 123-45-6789. {}",
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. ".repeat(150)
    );
    group.bench_function(BenchmarkId::new("large", large_text.len()), |b| {
        b.iter(|| detector.detect(black_box(&large_text)))
    });

    // Very large text (100KB)
    let very_large_text = format!(
        "Large document with scattered PII: email test@example.com, phone 555-123-4567. {}",
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. ".repeat(1500)
    );
    group.bench_function(BenchmarkId::new("very_large", very_large_text.len()), |b| {
        b.iter(|| detector.detect(black_box(&very_large_text)))
    });

    group.finish();
}

/// Benchmark multiple PII instances
fn bench_multiple_matches(c: &mut Criterion) {
    let detector = PIIDetector::new(PIIConfig {
        pattern_set: PatternSet::Standard,
        enable_validation: false,
        enable_context: false,
    });

    let mut group = c.benchmark_group("multiple_matches");

    // Single match
    group.bench_function("1_match", |b| {
        b.iter(|| detector.detect(black_box("Email: test@example.com")))
    });

    // 5 matches
    let text_5 = "Emails: test1@example.com, test2@example.com, test3@example.com, test4@example.com, test5@example.com";
    group.bench_function("5_matches", |b| {
        b.iter(|| detector.detect(black_box(text_5)))
    });

    // 10 matches
    let text_10 = format!(
        "{}, test6@example.com, test7@example.com, test8@example.com, test9@example.com, test10@example.com",
        text_5
    );
    group.bench_function("10_matches", |b| {
        b.iter(|| detector.detect(black_box(&text_10)))
    });

    // 20 matches
    let text_20 = format!(
        "{}, {}",
        text_10,
        "test11@example.com, test12@example.com, test13@example.com, test14@example.com, test15@example.com, test16@example.com, test17@example.com, test18@example.com, test19@example.com, test20@example.com"
    );
    group.bench_function("20_matches", |b| {
        b.iter(|| detector.detect(black_box(&text_20)))
    });

    group.finish();
}

/// Benchmark redaction strategies
fn bench_redaction(c: &mut Criterion) {
    let detector = PIIDetector::new(PIIConfig::default());
    let text = "Contact: test@example.com, SSN: 123-45-6789, Phone: 555-123-4567";
    let matches = detector.detect(text);

    let mut group = c.benchmark_group("redaction");

    group.bench_function("mask", |b| {
        b.iter(|| {
            redact(
                black_box(text),
                black_box(&matches),
                RedactionStrategy::Mask,
            )
        })
    });

    group.bench_function("hash", |b| {
        b.iter(|| {
            redact(
                black_box(text),
                black_box(&matches),
                RedactionStrategy::Hash,
            )
        })
    });

    group.bench_function("partial", |b| {
        b.iter(|| {
            redact(
                black_box(text),
                black_box(&matches),
                RedactionStrategy::Partial,
            )
        })
    });

    group.bench_function("token", |b| {
        b.iter(|| {
            redact(
                black_box(text),
                black_box(&matches),
                RedactionStrategy::Token,
            )
        })
    });

    group.bench_function("remove", |b| {
        b.iter(|| {
            redact(
                black_box(text),
                black_box(&matches),
                RedactionStrategy::Remove,
            )
        })
    });

    group.finish();
}

/// Benchmark full detect + redact workflow
fn bench_full_workflow(c: &mut Criterion) {
    let mut group = c.benchmark_group("full_workflow");

    let detector = PIIDetector::new(PIIConfig::default());
    let text = "User data: email test@example.com, SSN 123-45-6789, phone (555) 123-4567";

    group.bench_function("detect_and_redact", |b| {
        b.iter(|| {
            let matches = detector.detect(black_box(text));
            redact(black_box(text), &matches, RedactionStrategy::Mask)
        })
    });

    group.finish();
}

/// Benchmark realistic workload (mixed text with 0-5 PII instances)
fn bench_realistic_workload(c: &mut Criterion) {
    let detector = PIIDetector::new(PIIConfig {
        pattern_set: PatternSet::Standard,
        enable_validation: true,
        enable_context: false,
    });

    let mut group = c.benchmark_group("realistic");

    // Clean text (no PII)
    let clean_text = "This is a normal paragraph with no sensitive information. Lorem ipsum dolor sit amet, consectetur adipiscing elit.";
    group.bench_function("no_pii", |b| {
        b.iter(|| detector.detect(black_box(clean_text)))
    });

    // Low PII density (1-2 instances)
    let low_density = "User registered successfully. Confirmation sent to user@example.com. Please verify your account.";
    group.bench_function("low_density", |b| {
        b.iter(|| detector.detect(black_box(low_density)))
    });

    // Medium PII density (3-5 instances)
    let medium_density = "Profile updated: email test@example.com, phone 555-123-4567, backup phone 555-987-6543, IP 192.168.1.1";
    group.bench_function("medium_density", |b| {
        b.iter(|| detector.detect(black_box(medium_density)))
    });

    // High PII density (5+ instances)
    let high_density = "Contact card: John Doe, SSN 123-45-6789, email john@example.com, phone (555) 123-4567, mobile (555) 987-6543, address 192.168.1.1";
    group.bench_function("high_density", |b| {
        b.iter(|| detector.detect(black_box(high_density)))
    });

    group.finish();
}

/// Benchmark detector creation (initialization cost)
fn bench_detector_creation(c: &mut Criterion) {
    let mut group = c.benchmark_group("initialization");

    group.bench_function("create_detector", |b| {
        b.iter(|| {
            PIIDetector::new(black_box(PIIConfig {
                pattern_set: PatternSet::Standard,
                enable_validation: true,
                enable_context: false,
            }))
        })
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_individual_patterns,
    bench_with_validation,
    bench_pattern_sets,
    bench_text_sizes,
    bench_multiple_matches,
    bench_redaction,
    bench_full_workflow,
    bench_realistic_workload,
    bench_detector_creation,
);

criterion_main!(benches);
