//! OctoLLM Core Types
//!
//! Shared type definitions for OctoLLM services.

#![warn(missing_docs)]

use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Task contract for arm execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskContract {
    /// Unique task identifier
    pub task_id: Uuid,
    /// Task goal description
    pub goal: String,
}
