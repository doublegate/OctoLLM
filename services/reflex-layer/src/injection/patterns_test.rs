use lazy_static::lazy_static;
use regex::Regex;

lazy_static! {
    pub static ref TEST_PATTERN: Regex = Regex::new(
        r"(?i)(decode|decrypt)\s+(and\s+)?(execute|run)"
    ).unwrap();
}

#[test]
fn test_pattern() {
    assert!(TEST_PATTERN.is_match("decode and execute"));
}
