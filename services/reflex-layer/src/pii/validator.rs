// PII Validation Functions
//
// This module provides validation functions for various PII types to reduce false positives.

/// Validate a credit card number using the Luhn algorithm (mod-10 checksum)
///
/// # Arguments
///
/// * `number` - The credit card number as a string (may contain spaces or hyphens)
///
/// # Returns
///
/// `true` if the number passes Luhn validation, `false` otherwise
///
/// # Examples
///
/// ```
/// use reflex_layer::pii::validate_luhn;
///
/// assert!(validate_luhn("4532015112830366")); // Valid Visa
/// assert!(validate_luhn("5425233430109903")); // Valid MasterCard
/// assert!(!validate_luhn("1234567890123456")); // Invalid checksum
/// ```
pub fn validate_luhn(number: &str) -> bool {
    // Remove all non-digit characters
    let digits: Vec<u32> = number
        .chars()
        .filter(|c| c.is_ascii_digit())
        .filter_map(|c| c.to_digit(10))
        .collect();

    // Credit card numbers should be 13-19 digits
    if digits.len() < 13 || digits.len() > 19 {
        return false;
    }

    // Luhn algorithm: sum digits from right to left, doubling every second digit
    let checksum: u32 = digits
        .iter()
        .rev()
        .enumerate()
        .map(|(idx, &digit)| {
            if idx % 2 == 1 {
                // Double every second digit (from right)
                let doubled = digit * 2;
                if doubled > 9 {
                    doubled - 9 // Subtract 9 if result > 9 (equivalent to summing digits)
                } else {
                    doubled
                }
            } else {
                digit
            }
        })
        .sum();

    // Valid if checksum is divisible by 10
    checksum.is_multiple_of(10)
}

/// Validate a US Social Security Number
///
/// # Arguments
///
/// * `ssn` - The SSN as a string (may contain hyphens)
///
/// # Returns
///
/// `true` if the SSN passes validation rules, `false` otherwise
///
/// # Validation Rules
///
/// - Must be exactly 9 digits
/// - Area number (first 3 digits) must be 001-899 (excluding 666, 900-999)
/// - Group number (middle 2 digits) must be 01-99
/// - Serial number (last 4 digits) must be 0001-9999
///
/// # Examples
///
/// ```
/// use reflex_layer::pii::validate_ssn;
///
/// assert!(validate_ssn("123-45-6789")); // Valid
/// assert!(validate_ssn("456781234"));    // Valid (no hyphens)
/// assert!(!validate_ssn("000-12-3456")); // Invalid area (000)
/// assert!(!validate_ssn("666-12-3456")); // Invalid area (666)
/// assert!(!validate_ssn("900-12-3456")); // Invalid area (900+)
/// ```
pub fn validate_ssn(ssn: &str) -> bool {
    // Extract digits only
    let digits: String = ssn.chars().filter(|c| c.is_ascii_digit()).collect();

    // Must be exactly 9 digits
    if digits.len() != 9 {
        return false;
    }

    // Parse area, group, and serial numbers
    let area: u16 = match digits[0..3].parse() {
        Ok(n) => n,
        Err(_) => return false,
    };
    let group: u16 = match digits[3..5].parse() {
        Ok(n) => n,
        Err(_) => return false,
    };
    let serial: u16 = match digits[5..9].parse() {
        Ok(n) => n,
        Err(_) => return false,
    };

    // Validate area number (001-899, excluding 666 and 900-999)
    if area == 0 || area == 666 || area >= 900 {
        return false;
    }

    // Validate group number (01-99)
    if group == 0 {
        return false;
    }

    // Validate serial number (0001-9999)
    if serial == 0 {
        return false;
    }

    true
}

/// Validate an email address (basic RFC 5322 check)
///
/// # Arguments
///
/// * `email` - The email address to validate
///
/// # Returns
///
/// `true` if the email passes basic validation, `false` otherwise
///
/// # Note
///
/// This is a simplified validation. For production use, consider a full RFC 5322 parser.
pub fn validate_email(email: &str) -> bool {
    // Basic checks
    if !email.contains('@') {
        return false;
    }

    let parts: Vec<&str> = email.split('@').collect();
    if parts.len() != 2 {
        return false;
    }

    let (local, domain) = (parts[0], parts[1]);

    // Local part must not be empty
    if local.is_empty() {
        return false;
    }

    // Domain must contain at least one dot and have valid TLD
    if !domain.contains('.') {
        return false;
    }

    let domain_parts: Vec<&str> = domain.split('.').collect();
    if domain_parts.iter().any(|p| p.is_empty()) {
        return false;
    }

    // TLD must be at least 2 characters
    if let Some(tld) = domain_parts.last() {
        if tld.len() < 2 {
            return false;
        }
    } else {
        return false;
    }

    true
}

/// Validate a US phone number
///
/// # Arguments
///
/// * `phone` - The phone number to validate
///
/// # Returns
///
/// `true` if the phone number passes basic validation, `false` otherwise
pub fn validate_phone(phone: &str) -> bool {
    // Extract digits only
    let digits: String = phone.chars().filter(|c| c.is_ascii_digit()).collect();

    // US phone numbers should be 10 digits (or 11 with country code)
    if digits.len() != 10 && digits.len() != 11 {
        return false;
    }

    // If 11 digits, first digit must be 1 (US country code)
    if digits.len() == 11 && !digits.starts_with('1') {
        return false;
    }

    // Extract area code (first 3 digits of the 10-digit number)
    let offset = if digits.len() == 11 { 1 } else { 0 };
    let area_code: u16 = match digits[offset..offset + 3].parse() {
        Ok(n) => n,
        Err(_) => return false,
    };

    // Area code cannot start with 0 or 1
    if area_code < 200 {
        return false;
    }

    true
}

#[cfg(test)]
mod tests {
    use super::*;

    // Luhn algorithm tests
    #[test]
    fn test_luhn_valid_cards() {
        // Valid Visa
        assert!(validate_luhn("4532015112830366"));
        // Valid MasterCard
        assert!(validate_luhn("5425233430109903"));
        // Valid Amex
        assert!(validate_luhn("378282246310005"));
        // Valid with spaces
        assert!(validate_luhn("4532 0151 1283 0366"));
        // Valid with hyphens
        assert!(validate_luhn("4532-0151-1283-0366"));
    }

    #[test]
    fn test_luhn_invalid_cards() {
        // Invalid checksum
        assert!(!validate_luhn("4532015112830367"));
        // Random number
        assert!(!validate_luhn("1234567890123456"));
        // Too short
        assert!(!validate_luhn("123456789012"));
        // Too long
        assert!(!validate_luhn("12345678901234567890"));
    }

    // SSN validation tests
    #[test]
    fn test_ssn_valid() {
        assert!(validate_ssn("123-45-6789"));
        assert!(validate_ssn("123456789")); // No hyphens (note: must match pattern constraints)
        assert!(validate_ssn("123 45 6789")); // Spaces (digits extracted)
    }

    #[test]
    fn test_ssn_invalid_area() {
        assert!(!validate_ssn("000-12-3456")); // Area = 000
        assert!(!validate_ssn("666-12-3456")); // Area = 666 (forbidden)
        assert!(!validate_ssn("900-12-3456")); // Area >= 900
        assert!(!validate_ssn("950-12-3456")); // Area >= 900
    }

    #[test]
    fn test_ssn_invalid_group() {
        assert!(!validate_ssn("123-00-6789")); // Group = 00
    }

    #[test]
    fn test_ssn_invalid_serial() {
        assert!(!validate_ssn("123-45-0000")); // Serial = 0000
    }

    #[test]
    fn test_ssn_invalid_length() {
        assert!(!validate_ssn("123-45-678")); // Too short
        assert!(!validate_ssn("123-45-67890")); // Too long
    }

    // Email validation tests
    #[test]
    fn test_email_valid() {
        assert!(validate_email("user@example.com"));
        assert!(validate_email("test.user+tag@sub.example.co.uk"));
        assert!(validate_email("a@b.co"));
    }

    #[test]
    fn test_email_invalid() {
        assert!(!validate_email("not-an-email"));
        assert!(!validate_email("@example.com")); // Empty local part
        assert!(!validate_email("user@")); // Empty domain
        assert!(!validate_email("user@domain")); // No TLD
        assert!(!validate_email("user@.com")); // Empty domain part
        assert!(!validate_email("user@domain.c")); // TLD too short
    }

    // Phone validation tests
    #[test]
    fn test_phone_valid() {
        assert!(validate_phone("555-123-4567")); // 10 digits
        assert!(validate_phone("(555) 123-4567")); // 10 digits with parens
        assert!(validate_phone("+1-555-123-4567")); // 11 digits with country code
        assert!(validate_phone("1-555-123-4567")); // 11 digits with country code
    }

    #[test]
    fn test_phone_invalid() {
        assert!(!validate_phone("123-456-7890")); // Area code starts with 1
        assert!(!validate_phone("023-456-7890")); // Area code starts with 0
        assert!(!validate_phone("555-1234")); // Too short
        assert!(!validate_phone("2-555-123-4567")); // Country code not 1
    }
}
