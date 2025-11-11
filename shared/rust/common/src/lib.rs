//! OctoLLM Common Utilities
//!
//! Shared utilities and helper functions for OctoLLM services.

#![warn(missing_docs)]

/// Common error types
pub mod error {
    use thiserror::Error;

    /// Common error type for OctoLLM operations
    #[derive(Error, Debug)]
    pub enum OctoLLMError {
        /// Generic error
        #[error("Internal error: {0}")]
        Internal(String),
    }
}
