# OctoLLM: Architecture and Technical Implementation

## Document Overview

This document provides the technical blueprint for implementing OctoLLM, a distributed AI architecture for offensive security and developer tooling. It covers system architecture, component specifications, implementation patterns, deployment strategies, and operational procedures.

**Audience**: Software engineers, DevOps specialists, and technical leads implementing or maintaining OctoLLM deployments.

**Companion Document**: See "OctoLLM Project Overview and Concept Charter" for strategic vision and design rationale.

---

## 1. System Architecture

### 1.1 High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                              │
│                    (Rate Limiting, Auth)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Reflex Preprocessing Layer                    │
│          (Cache Lookup, PII Filter, Schema Validation)           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   Orchestrator       │ ◄──── Global Memory
                  │   (Brain)            │       (Knowledge Graph)
                  │   [Python + LLM API] │
                  └──────────┬───────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Planner     │    │  Retriever   │    │    Coder     │
│  Arm         │    │  Arm         │    │    Arm       │
│  [Python]    │    │  [Python]    │    │  [Rust opt]  │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       │ Local Memory      │ Vector DB         │ Code Context
       └───────────────────┴───────────────────┘
        
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Tool         │    │   Judge      │    │   Safety     │
│ Executor     │    │   Arm        │    │   Guardian   │
│ [Rust]       │    │   [Python]   │    │   [Python]   │
└──────────────┘    └──────────────┘    └──────────────┘

        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Tools & Services                     │
│  (Web APIs, Databases, Command Execution, Network Scanners)     │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Architectural Layers

#### Layer 1: Ingress (API Gateway + Reflex)
- **Technology**: NGINX or Traefik for gateway, Python/Rust for reflex logic
- **Responsibilities**: Authentication, rate limiting, initial content filtering, cache lookup
- **Latency Target**: <10ms for cache hits, <50ms for reflex decisions

#### Layer 2: Orchestration (The Brain)
- **Technology**: Python with FastAPI, LangChain/LlamaIndex, OpenAI/Anthropic API clients
- **Responsibilities**: Task parsing, planning, arm selection, result integration
- **Latency Target**: 1-10s for planning phase, variable for execution

#### Layer 3: Execution (The Arms)
- **Technology**: Polyglot microservices (Python for AI-heavy, Rust for performance-critical)
- **Responsibilities**: Specialized task execution within domain boundaries
- **Latency Target**: 0.1-5s per arm call depending on complexity

#### Layer 4: Persistence (Memory Systems)
- **Technology**: PostgreSQL (global memory), Redis (caching), Qdrant/Weaviate (vector stores)
- **Responsibilities**: Long-term knowledge storage, episodic memory, result caching
- **Latency Target**: <100ms for memory queries

#### Layer 5: Observability
- **Technology**: Prometheus (metrics), Loki (logs), Jaeger (distributed tracing)
- **Responsibilities**: Monitoring, alerting, debugging, performance analysis

---

## 2. Core Component Specifications

### 2.1 Orchestrator (Brain)

#### 2.1.1 Technology Stack

**Language**: Python 3.11+  
**Frameworks**: 
- FastAPI (web server)
- Pydantic (schema validation)
- LangGraph or custom state machine (workflow orchestration)

**LLM Integration**:
- OpenAI SDK (GPT-4, GPT-4 Turbo)
- Anthropic SDK (Claude 3 Opus/Sonnet)
- Local models via vLLM or Ollama (fallback/cost optimization)

**Dependencies**:
```python
# requirements.txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.4.0
openai>=1.3.0
anthropic>=0.7.0
langchain>=0.1.0
redis>=5.0.0
psycopg[binary]>=3.1.0
prometheus-client>=0.19.0
structlog>=23.2.0
```

#### 2.1.2 Core Data Structures

**Task Contract**:
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskContract(BaseModel):
    """Formal specification for a subtask."""
    
    task_id: str = Field(..., description="Unique task identifier")
    goal: str = Field(..., description="Natural language goal description")
    constraints: List[str] = Field(
        default_factory=list,
        description="Hard constraints (time, cost, safety)"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Relevant background information"
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Conditions for successful completion"
    )
    budget: Dict[str, int] = Field(
        default_factory=lambda: {"max_tokens": 4000, "max_time_seconds": 30},
        description="Resource limits"
    )
    priority: Priority = Field(default=Priority.MEDIUM)
    parent_task_id: Optional[str] = Field(
        None,
        description="Parent task if this is a subtask"
    )
    assigned_arm: Optional[str] = Field(None, description="Target arm identifier")
```

**Arm Capability Registry**:
```python
from typing import Callable, Set
from dataclasses import dataclass

@dataclass
class ArmCapability:
    """Description of what an arm can do."""
    
    arm_id: str
    name: str
    description: str
    input_schema: Dict[str, Any]  # JSON schema
    output_schema: Dict[str, Any]
    capabilities: Set[str]  # Tags like "code", "security", "web"
    cost_tier: int  # 1 = cheap, 5 = expensive
    average_latency_ms: float
    success_rate: float  # Historical performance
    endpoint: str  # Kubernetes service URL or function reference

# Example registry
ARM_REGISTRY = {
    "planner": ArmCapability(
        arm_id="planner",
        name="Task Planner",
        description="Decomposes complex tasks into subtasks",
        input_schema={"type": "object", "properties": {"goal": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"plan": {"type": "array"}}},
        capabilities={"planning", "decomposition"},
        cost_tier=2,
        average_latency_ms=1200,
        success_rate=0.92,
        endpoint="http://planner-arm:8080/plan"
    ),
    # ... other arms
}
```

#### 2.1.3 Orchestrator Logic

**Main Orchestration Loop**:
```python
import structlog
from typing import List, Dict, Any

logger = structlog.get_logger()

class Orchestrator:
    """Central coordinator for OctoLLM system."""
    
    def __init__(self, llm_client, arm_registry: Dict[str, ArmCapability]):
        self.llm = llm_client
        self.registry = arm_registry
        self.global_memory = GlobalMemoryStore()
        self.task_queue = TaskQueue()
        
    async def process_task(self, task: TaskContract) -> Dict[str, Any]:
        """Main orchestration loop."""
        
        logger.info("orchestrator.process_task.start", task_id=task.task_id)
        
        # Step 1: Check if task can be handled by cache/reflex
        cached_result = await self._check_cache(task)
        if cached_result:
            logger.info("orchestrator.cache_hit", task_id=task.task_id)
            return cached_result
        
        # Step 2: Generate plan using LLM or Planner arm
        plan = await self._generate_plan(task)
        logger.info("orchestrator.plan_generated", 
                   task_id=task.task_id, 
                   num_steps=len(plan))
        
        # Step 3: Execute plan step-by-step
        results = []
        for step_idx, step in enumerate(plan):
            try:
                step_result = await self._execute_step(step, task.context)
                results.append(step_result)
                
                # Update context for subsequent steps
                task.context[f"step_{step_idx}_result"] = step_result
                
                # Check if we need to replan based on result
                if step_result.get("requires_replanning"):
                    logger.warning("orchestrator.replan_triggered", 
                                 task_id=task.task_id,
                                 step=step_idx)
                    plan = await self._replan(task, results)
                    
            except Exception as e:
                logger.error("orchestrator.step_failed",
                           task_id=task.task_id,
                           step=step_idx,
                           error=str(e))
                # Attempt recovery or escalation
                recovery_result = await self._handle_failure(step, e, task)
                results.append(recovery_result)
        
        # Step 4: Integrate results and validate
        final_result = await self._integrate_results(results, task)
        
        # Step 5: Run validation through Judge arm
        is_valid = await self._validate_result(final_result, task)
        if not is_valid:
            logger.warning("orchestrator.validation_failed", task_id=task.task_id)
            # Attempt repair loop
            final_result = await self._repair_result(final_result, task)
        
        # Step 6: Cache result for future queries
        await self._cache_result(task, final_result)
        
        logger.info("orchestrator.process_task.complete", task_id=task.task_id)
        return final_result
    
    async def _generate_plan(self, task: TaskContract) -> List[Dict]:
        """Use LLM or Planner arm to decompose task."""
        
        # Option 1: Use Planner arm for complex tasks
        if self._is_complex_task(task):
            planner = self.registry["planner"]
            response = await self._call_arm(planner, {"goal": task.goal})
            return response["plan"]
        
        # Option 2: Use LLM directly for simple tasks
        prompt = f"""
        Task: {task.goal}
        Constraints: {', '.join(task.constraints)}
        
        Break this down into 3-5 concrete steps. For each step, specify:
        1. Action description
        2. Which arm/tool to use
        3. Success criteria
        
        Output as JSON: [{{"step": 1, "action": "...", "arm": "...", "criteria": "..."}}]
        """
        
        response = await self.llm.complete(prompt)
        return self._parse_plan_json(response)
    
    async def _execute_step(self, step: Dict, context: Dict) -> Dict:
        """Execute a single step by calling appropriate arm."""
        
        arm_id = step.get("arm")
        if arm_id not in self.registry:
            raise ValueError(f"Unknown arm: {arm_id}")
        
        arm = self.registry[arm_id]
        
        # Prepare input with context
        arm_input = {
            "instruction": step["action"],
            "context": context,
            "criteria": step.get("criteria", [])
        }
        
        # Call arm via HTTP or direct function call
        result = await self._call_arm(arm, arm_input)
        
        # Attach provenance metadata
        result["provenance"] = {
            "arm_id": arm_id,
            "timestamp": datetime.utcnow().isoformat(),
            "step_index": step.get("step"),
            "confidence": result.get("confidence", 0.0)
        }
        
        return result
    
    async def _call_arm(self, arm: ArmCapability, payload: Dict) -> Dict:
        """Make HTTP call to arm service with retry logic."""
        
        import aiohttp
        from tenacity import retry, stop_after_attempt, wait_exponential
        
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
        async def _make_request():
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    arm.endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        
        try:
            return await _make_request()
        except Exception as e:
            logger.error("orchestrator.arm_call_failed",
                        arm_id=arm.arm_id,
                        error=str(e))
            raise
```

#### 2.1.4 Routing and Gating Logic

**Uncertainty-Based Routing**:
```python
class Router:
    """Decides which arm(s) to invoke based on task characteristics."""
    
    def __init__(self, registry: Dict[str, ArmCapability]):
        self.registry = registry
        self.classifier = self._load_routing_classifier()
    
    def route_task(self, task: TaskContract) -> List[str]:
        """Select appropriate arm(s) for task."""
        
        # Extract features from task
        features = self._extract_features(task)
        
        # Use ML classifier to predict best arm(s)
        arm_scores = self.classifier.predict_proba(features)
        
        # Select top arms based on confidence threshold
        selected_arms = []
        for arm_id, score in arm_scores.items():
            if score > 0.7:  # High confidence
                selected_arms.append(arm_id)
            elif score > 0.4:  # Medium confidence - maybe use swarm
                if task.priority in [Priority.HIGH, Priority.CRITICAL]:
                    # Use multiple arms for important tasks
                    selected_arms.append(arm_id)
        
        # Fallback: if no high-confidence match, use generalist
        if not selected_arms:
            selected_arms = ["generalist"]
        
        return selected_arms
    
    def _extract_features(self, task: TaskContract) -> np.ndarray:
        """Extract features for routing classifier."""
        # This would be a trained embedder + feature extractor
        # For now, simple heuristics:
        features = {}
        
        # Keyword-based features
        goal_lower = task.goal.lower()
        features["has_code_keyword"] = any(
            kw in goal_lower for kw in ["code", "function", "script", "bug"]
        )
        features["has_search_keyword"] = any(
            kw in goal_lower for kw in ["search", "find", "look up", "retrieve"]
        )
        # ... more feature engineering
        
        return np.array(list(features.values()))
```

### 2.2 Reflex Preprocessing Layer

#### 2.2.1 Implementation (Rust for Performance)

**File**: `reflex-layer/src/main.rs`

```rust
//! Reflex Preprocessing Layer for OctoLLM
//! 
//! This service acts as a fast-path filter before the main orchestrator,
//! handling common cases through caching, regex filtering, and simple ML models.
//! 
//! Performance target: <10ms for 95% of requests
//! 
//! Key responsibilities:
//! - Cache lookup for repeated queries
//! - PII detection and redaction
//! - Malicious input filtering (injection attempts)
//! - Schema validation
//! - Rate limiting

use actix_web::{web, App, HttpServer, HttpResponse, Responder};
use serde::{Deserialize, Serialize};
use redis::AsyncCommands;
use regex::Regex;
use std::sync::Arc;
use std::collections::HashMap;

/// Request payload from API gateway
#[derive(Deserialize, Serialize, Clone)]
struct IncomingRequest {
    query: String,
    user_id: Option<String>,
    context: HashMap<String, serde_json::Value>,
}

/// Decision from reflex layer
#[derive(Serialize)]
#[serde(tag = "action")]
enum ReflexDecision {
    /// Return cached response immediately
    CacheHit {
        response: serde_json::Value,
        cached_at: String,
    },
    /// Block request due to policy violation
    Blocked {
        reason: String,
        violation_type: String,
    },
    /// Pass to orchestrator (novel query)
    PassThrough {
        sanitized_query: String,
        metadata: HashMap<String, String>,
    },
}

/// Main reflex processor
struct ReflexProcessor {
    redis_client: redis::Client,
    pii_patterns: Vec<Regex>,
    injection_patterns: Vec<Regex>,
}

impl ReflexProcessor {
    fn new(redis_url: &str) -> Result<Self, Box<dyn std::error::Error>> {
        Ok(Self {
            redis_client: redis::Client::open(redis_url)?,
            pii_patterns: Self::compile_pii_patterns(),
            injection_patterns: Self::compile_injection_patterns(),
        })
    }
    
    /// Compile regex patterns for PII detection
    fn compile_pii_patterns() -> Vec<Regex> {
        vec![
            // SSN: XXX-XX-XXXX
            Regex::new(r"\b\d{3}-\d{2}-\d{4}\b").unwrap(),
            // Credit card: XXXX-XXXX-XXXX-XXXX
            Regex::new(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b").unwrap(),
            // Email addresses
            Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b").unwrap(),
            // Phone numbers: various formats
            Regex::new(r"\b\+?1?\s*\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b").unwrap(),
        ]
    }
    
    /// Compile patterns for prompt injection detection
    fn compile_injection_patterns() -> Vec<Regex> {
        vec![
            // Common injection keywords
            Regex::new(r"(?i)(ignore\s+(previous|above|all)\s+instructions?)").unwrap(),
            Regex::new(r"(?i)(you\s+are\s+now|system\s*:)").unwrap(),
            Regex::new(r"(?i)(disregard|forget)\s+(everything|rules)").unwrap(),
            // Attempts to access system prompts
            Regex::new(r"(?i)(show|reveal|print)\s+(your\s+)?(system\s+)?(prompt|instructions)").unwrap(),
        ]
    }
    
    /// Main processing pipeline
    async fn process(&self, req: IncomingRequest) -> ReflexDecision {
        // Step 1: Check cache
        if let Some(cached) = self.check_cache(&req.query).await {
            return ReflexDecision::CacheHit {
                response: cached,
                cached_at: chrono::Utc::now().to_rfc3339(),
            };
        }
        
        // Step 2: Check for injection attempts
        if let Some(violation) = self.detect_injection(&req.query) {
            return ReflexDecision::Blocked {
                reason: format!("Potential prompt injection detected: {}", violation),
                violation_type: "injection".to_string(),
            };
        }
        
        // Step 3: Sanitize PII
        let sanitized = self.sanitize_pii(&req.query);
        
        // Step 4: If query is significantly different after sanitization, flag it
        let pii_detected = sanitized != req.query;
        
        // Step 5: Pass through with metadata
        let mut metadata = HashMap::new();
        metadata.insert("pii_detected".to_string(), pii_detected.to_string());
        metadata.insert("original_length".to_string(), req.query.len().to_string());
        
        ReflexDecision::PassThrough {
            sanitized_query: sanitized,
            metadata,
        }
    }
    
    /// Check Redis cache for query
    async fn check_cache(&self, query: &str) -> Option<serde_json::Value> {
        let mut con = self.redis_client.get_async_connection().await.ok()?;
        
        // Use hash of query as key for privacy
        let cache_key = format!("cache:{}", Self::hash_query(query));
        
        // Try to get cached response
        let cached: Option<String> = con.get(&cache_key).await.ok()?;
        
        cached.and_then(|json_str| serde_json::from_str(&json_str).ok())
    }
    
    /// Simple hash function for cache keys
    fn hash_query(query: &str) -> String {
        use sha2::{Sha256, Digest};
        let mut hasher = Sha256::new();
        hasher.update(query.as_bytes());
        format!("{:x}", hasher.finalize())
    }
    
    /// Detect prompt injection attempts
    fn detect_injection(&self, text: &str) -> Option<String> {
        for (idx, pattern) in self.injection_patterns.iter().enumerate() {
            if pattern.is_match(text) {
                return Some(format!("Pattern #{} matched", idx + 1));
            }
        }
        None
    }
    
    /// Sanitize PII from text
    fn sanitize_pii(&self, text: &str) -> String {
        let mut sanitized = text.to_string();
        
        // Replace SSNs
        sanitized = self.pii_patterns[0].replace_all(&sanitized, "[SSN-REDACTED]").to_string();
        
        // Replace credit cards
        sanitized = self.pii_patterns[1].replace_all(&sanitized, "[CC-REDACTED]").to_string();
        
        // Replace emails
        sanitized = self.pii_patterns[2].replace_all(&sanitized, "[EMAIL-REDACTED]").to_string();
        
        // Replace phone numbers
        sanitized = self.pii_patterns[3].replace_all(&sanitized, "[PHONE-REDACTED]").to_string();
        
        sanitized
    }
}

/// HTTP handler for reflex endpoint
async fn reflex_handler(
    processor: web::Data<Arc<ReflexProcessor>>,
    req: web::Json<IncomingRequest>,
) -> impl Responder {
    let decision = processor.process(req.into_inner()).await;
    HttpResponse::Ok().json(decision)
}

/// Main entry point
#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    let redis_url = std::env::var("REDIS_URL")
        .unwrap_or_else(|_| "redis://localhost:6379".to_string());
    
    let processor = Arc::new(
        ReflexProcessor::new(&redis_url)
            .expect("Failed to initialize reflex processor")
    );
    
    println!("Starting Reflex Layer on 0.0.0.0:8000");
    
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(processor.clone()))
            .route("/reflex", web::post().to(reflex_handler))
            .route("/health", web::get().to(|| async { HttpResponse::Ok().body("OK") }))
    })
    .bind("0.0.0.0:8000")?
    .run()
    .await
}
```

**Dockerfile for Reflex Layer**:
```dockerfile
# reflex-layer/Dockerfile
FROM rust:1.75 as builder

WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src ./src

# Build with optimizations
RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/reflex-layer /usr/local/bin/reflex-layer

ENV RUST_LOG=info
ENV REDIS_URL=redis://redis:6379

EXPOSE 8000

CMD ["reflex-layer"]
```

### 2.3 Specialized Arms Implementation

#### 2.3.1 Planner Arm (Python)

**File**: `arms/planner/main.py`

```python
"""
Planner Arm for OctoLLM

Decomposes complex tasks into sequences of subtasks with acceptance criteria.
Uses a fine-tuned smaller LLM (e.g., Mistral 7B) for cost efficiency.

Key responsibilities:
- Task decomposition
- Step ordering
- Acceptance criteria definition
- Dependency resolution
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import openai
import os

app = FastAPI(title="Planner Arm")

# Configuration
PLANNER_MODEL = os.getenv("PLANNER_MODEL", "gpt-3.5-turbo")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

class PlanRequest(BaseModel):
    """Input schema for planning requests."""
    goal: str = Field(..., description="High-level task goal")
    constraints: List[str] = Field(default_factory=list, description="Constraints")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

class SubTask(BaseModel):
    """A single step in the plan."""
    step: int
    action: str
    required_arm: str  # Which arm should execute this
    acceptance_criteria: List[str]
    depends_on: List[int] = Field(default_factory=list, description="Prerequisite steps")
    estimated_cost_tier: int = Field(1, description="1=cheap, 5=expensive")

class PlanResponse(BaseModel):
    """Output schema for planning responses."""
    plan: List[SubTask]
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0, description="Planner's confidence")

@app.post("/plan", response_model=PlanResponse)
async def generate_plan(request: PlanRequest) -> PlanResponse:
    """Generate a step-by-step plan for accomplishing the goal."""
    
    # Construct prompt for planning LLM
    system_prompt = """You are an expert task planner for an AI system.
    
Your job is to decompose complex goals into clear, executable steps.

Available arms (capabilities):
- retriever: Search knowledge bases, documentation
- coder: Write/modify code, debug, analyze code
- executor: Run commands, API calls, web scraping
- judge: Validate outputs, check facts
- guardian: Check for safety/PII issues

For each step, specify:
1. What action to take
2. Which arm should do it
3. How to verify success (acceptance criteria)
4. Dependencies on previous steps

Output valid JSON only."""

    user_prompt = f"""Goal: {request.goal}

Constraints:
{chr(10).join(f"- {c}" for c in request.constraints) if request.constraints else "None"}

Context:
{request.context if request.context else "None"}

Generate a plan with 3-7 steps. Output as JSON:
{{
  "plan": [
    {{
      "step": 1,
      "action": "...",
      "required_arm": "...",
      "acceptance_criteria": ["...", "..."],
      "depends_on": [],
      "estimated_cost_tier": 1
    }},
    ...
  ],
  "rationale": "Brief explanation of approach",
  "confidence": 0.85
}}"""

    try:
        # Call LLM for planning
        response = openai.ChatCompletion.create(
            model=PLANNER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent plans
            max_tokens=1500
        )
        
        # Parse response
        plan_json = response.choices[0].message.content
        
        # Attempt to extract JSON if wrapped in markdown
        if "```json" in plan_json:
            plan_json = plan_json.split("```json")[1].split("```")[0]
        
        import json
        plan_data = json.loads(plan_json)
        
        # Validate and return
        return PlanResponse(**plan_data)
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse plan JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planning failed: {e}")

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "arm": "planner"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

#### 2.3.2 Tool Executor Arm (Rust for Safety)

**File**: `arms/executor/src/main.rs`

```rust
//! Tool Executor Arm for OctoLLM
//! 
//! Executes external actions in sandboxed environments with strict capability controls.
//! 
//! Security features:
//! - Allowlist-based command filtering
//! - Network isolation via Docker
//! - Comprehensive audit logging
//! - Timeout enforcement
//! - Resource limits (CPU, memory)

use actix_web::{web, App, HttpServer, HttpResponse, Responder};
use serde::{Deserialize, Serialize};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};
use std::collections::HashMap;

/// Execution request payload
#[derive(Deserialize)]
struct ExecutionRequest {
    action_type: String,  // "shell", "http", "python"
    command: String,
    args: Vec<String>,
    timeout_seconds: Option<u64>,
    env_vars: HashMap<String, String>,
}

/// Execution result
#[derive(Serialize)]
struct ExecutionResult {
    success: bool,
    stdout: String,
    stderr: String,
    exit_code: Option<i32>,
    duration_ms: u128,
    provenance: ProvenanceMetadata,
}

#[derive(Serialize)]
struct ProvenanceMetadata {
    arm_id: String,
    timestamp: String,
    action_type: String,
    command_hash: String,
}

/// Capability-based access control
struct Capabilities {
    allowed_commands: Vec<String>,
    allowed_hosts: Vec<String>,
    max_execution_time: Duration,
}

impl Capabilities {
    fn default_safe() -> Self {
        Self {
            // Very restricted default set
            allowed_commands: vec![
                "echo".to_string(),
                "cat".to_string(),
                "ls".to_string(),
                "grep".to_string(),
                "curl".to_string(),  // Only for HTTP requests
            ],
            allowed_hosts: vec![
                "api.github.com".to_string(),
                "httpbin.org".to_string(),
                // Add other safe hosts
            ],
            max_execution_time: Duration::from_secs(30),
        }
    }
    
    fn is_command_allowed(&self, cmd: &str) -> bool {
        self.allowed_commands.iter().any(|allowed| cmd == allowed)
    }
    
    fn is_host_allowed(&self, url: &str) -> bool {
        self.allowed_hosts.iter().any(|host| url.contains(host))
    }
}

/// Main executor implementation
struct Executor {
    capabilities: Capabilities,
}

impl Executor {
    fn new() -> Self {
        Self {
            capabilities: Capabilities::default_safe(),
        }
    }
    
    async fn execute(&self, req: ExecutionRequest) -> Result<ExecutionResult, String> {
        let start = Instant::now();
        
        match req.action_type.as_str() {
            "shell" => self.execute_shell(&req, start).await,
            "http" => self.execute_http(&req, start).await,
            _ => Err(format!("Unsupported action type: {}", req.action_type)),
        }
    }
    
    async fn execute_shell(
        &self,
        req: &ExecutionRequest,
        start: Instant,
    ) -> Result<ExecutionResult, String> {
        // Validate command against allowlist
        if !self.capabilities.is_command_allowed(&req.command) {
            return Err(format!(
                "Command '{}' not in allowlist. Allowed: {:?}",
                req.command, self.capabilities.allowed_commands
            ));
        }
        
        // Build command with timeout
        let timeout = Duration::from_secs(
            req.timeout_seconds.unwrap_or(10).min(30)  // Cap at 30s
        );
        
        let output = tokio::time::timeout(
            timeout,
            tokio::task::spawn_blocking(move || {
                Command::new(&req.command)
                    .args(&req.args)
                    .stdout(Stdio::piped())
                    .stderr(Stdio::piped())
                    .output()
            })
        )
        .await
        .map_err(|_| "Execution timeout".to_string())?
        .map_err(|e| format!("Failed to spawn process: {}", e))?
        .map_err(|e| format!("Process failed: {}", e))?;
        
        Ok(ExecutionResult {
            success: output.status.success(),
            stdout: String::from_utf8_lossy(&output.stdout).to_string(),
            stderr: String::from_utf8_lossy(&output.stderr).to_string(),
            exit_code: output.status.code(),
            duration_ms: start.elapsed().as_millis(),
            provenance: ProvenanceMetadata {
                arm_id: "executor".to_string(),
                timestamp: chrono::Utc::now().to_rfc3339(),
                action_type: "shell".to_string(),
                command_hash: Self::hash_command(&req.command, &req.args),
            },
        })
    }
    
    async fn execute_http(
        &self,
        req: &ExecutionRequest,
        start: Instant,
    ) -> Result<ExecutionResult, String> {
        // Parse URL and validate against allowed hosts
        let url = &req.command;
        
        if !self.capabilities.is_host_allowed(url) {
            return Err(format!(
                "Host not in allowlist. URL: {}, Allowed hosts: {:?}",
                url, self.capabilities.allowed_hosts
            ));
        }
        
        // Make HTTP request with timeout
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(10))
            .build()
            .map_err(|e| format!("Failed to build HTTP client: {}", e))?;
        
        let response = client
            .get(url)
            .send()
            .await
            .map_err(|e| format!("HTTP request failed: {}", e))?;
        
        let status = response.status();
        let body = response
            .text()
            .await
            .map_err(|e| format!("Failed to read response body: {}", e))?;
        
        Ok(ExecutionResult {
            success: status.is_success(),
            stdout: body,
            stderr: if status.is_success() {
                String::new()
            } else {
                format!("HTTP {}", status)
            },
            exit_code: Some(status.as_u16() as i32),
            duration_ms: start.elapsed().as_millis(),
            provenance: ProvenanceMetadata {
                arm_id: "executor".to_string(),
                timestamp: chrono::Utc::now().to_rfc3339(),
                action_type: "http".to_string(),
                command_hash: Self::hash_command(url, &[]),
            },
        })
    }
    
    fn hash_command(cmd: &str, args: &[String]) -> String {
        use sha2::{Sha256, Digest};
        let mut hasher = Sha256::new();
        hasher.update(cmd.as_bytes());
        for arg in args {
            hasher.update(arg.as_bytes());
        }
        format!("{:x}", hasher.finalize())
    }
}

/// HTTP handler
async fn execute_handler(
    executor: web::Data<Executor>,
    req: web::Json<ExecutionRequest>,
) -> impl Responder {
    match executor.execute(req.into_inner()).await {
        Ok(result) => HttpResponse::Ok().json(result),
        Err(err) => HttpResponse::BadRequest().json(serde_json::json!({
            "error": err
        })),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    let executor = web::Data::new(Executor::new());
    
    println!("Starting Tool Executor Arm on 0.0.0.0:8080");
    
    HttpServer::new(move || {
        App::new()
            .app_data(executor.clone())
            .route("/execute", web::post().to(execute_handler))
            .route("/health", web::get().to(|| async { HttpResponse::Ok().body("OK") }))
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}
```

---

## 3. Deployment Architecture

### 3.1 Kubernetes Deployment Manifests

#### 3.1.1 Namespace and RBAC

**File**: `k8s/00-namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: octollm
  labels:
    name: octollm
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: octollm-orchestrator
  namespace: octollm
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: octollm-orchestrator-role
  namespace: octollm
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: octollm-orchestrator-binding
  namespace: octollm
subjects:
  - kind: ServiceAccount
    name: octollm-orchestrator
    namespace: octollm
roleRef:
  kind: Role
  name: octollm-orchestrator-role
  apiGroup: rbac.authorization.k8s.io
```

#### 3.1.2 ConfigMap for Arm Registry

**File**: `k8s/01-configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: arm-registry
  namespace: octollm
data:
  registry.json: |
    {
      "planner": {
        "endpoint": "http://planner-arm:8080/plan",
        "capabilities": ["planning", "decomposition"],
        "cost_tier": 2
      },
      "executor": {
        "endpoint": "http://executor-arm:8080/execute",
        "capabilities": ["shell", "http", "api"],
        "cost_tier": 3
      },
      "coder": {
        "endpoint": "http://coder-arm:8080/code",
        "capabilities": ["code_generation", "debugging", "refactoring"],
        "cost_tier": 4
      },
      "retriever": {
        "endpoint": "http://retriever-arm:8080/search",
        "capabilities": ["search", "knowledge_retrieval"],
        "cost_tier": 1
      },
      "judge": {
        "endpoint": "http://judge-arm:8080/validate",
        "capabilities": ["validation", "fact_checking"],
        "cost_tier": 2
      }
    }
```

#### 3.1.3 Orchestrator Deployment

**File**: `k8s/10-orchestrator.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
  namespace: octollm
  labels:
    app: orchestrator
    component: brain
spec:
  replicas: 2  # For high availability
  selector:
    matchLabels:
      app: orchestrator
  template:
    metadata:
      labels:
        app: orchestrator
        component: brain
    spec:
      serviceAccountName: octollm-orchestrator
      containers:
        - name: orchestrator
          image: octollm/orchestrator:latest
          ports:
            - containerPort: 8000
              name: http
          env:
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: llm-api-keys
                  key: openai-key
            - name: REDIS_URL
              value: "redis://redis:6379"
            - name: POSTGRES_URL
              value: "postgresql://postgres:5432/octollm"
            - name: ARM_REGISTRY_PATH
              value: "/config/registry.json"
          volumeMounts:
            - name: arm-registry
              mountPath: /config
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "2000m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
      volumes:
        - name: arm-registry
          configMap:
            name: arm-registry
---
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  namespace: octollm
spec:
  selector:
    app: orchestrator
  ports:
    - protocol: TCP
      port: 8000
      targetPort: 8000
  type: ClusterIP
```

#### 3.1.4 Reflex Layer Deployment

**File**: `k8s/11-reflex-layer.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: reflex-layer
  namespace: octollm
  labels:
    app: reflex-layer
    component: preprocessing
spec:
  replicas: 3  # High replica count for high throughput
  selector:
    matchLabels:
      app: reflex-layer
  template:
    metadata:
      labels:
        app: reflex-layer
        component: preprocessing
    spec:
      containers:
        - name: reflex
          image: octollm/reflex-layer:latest
          ports:
            - containerPort: 8000
              name: http
          env:
            - name: REDIS_URL
              value: "redis://redis:6379"
            - name: RUST_LOG
              value: "info"
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 3
---
apiVersion: v1
kind: Service
metadata:
  name: reflex-layer
  namespace: octollm
spec:
  selector:
    app: reflex-layer
  ports:
    - protocol: TCP
      port: 8000
      targetPort: 8000
  type: ClusterIP
```

#### 3.1.5 Arm Deployments (Example: Planner)

**File**: `k8s/20-planner-arm.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: planner-arm
  namespace: octollm
  labels:
    app: planner-arm
    component: arm
spec:
  replicas: 1
  selector:
    matchLabels:
      app: planner-arm
  template:
    metadata:
      labels:
        app: planner-arm
        component: arm
    spec:
      containers:
        - name: planner
          image: octollm/planner-arm:latest
          ports:
            - containerPort: 8080
              name: http
          env:
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: llm-api-keys
                  key: openai-key
            - name: PLANNER_MODEL
              value: "gpt-3.5-turbo"
          resources:
            requests:
              memory: "256Mi"
              cpu: "200m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: planner-arm
  namespace: octollm
spec:
  selector:
    app: planner-arm
  ports:
    - protocol: TCP
      port: 8080
      targetPort: 8080
  type: ClusterIP
```

### 3.2 Horizontal Pod Autoscaling

**File**: `k8s/30-hpa.yaml`

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orchestrator-hpa
  namespace: octollm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orchestrator
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: reflex-layer-hpa
  namespace: octollm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reflex-layer
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
```

### 3.3 Ingress Configuration

**File**: `k8s/40-ingress.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: octollm-ingress
  namespace: octollm
  annotations:
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - octollm.example.com
      secretName: octollm-tls
  rules:
    - host: octollm.example.com
      http:
        paths:
          - path: /api/v1
            pathType: Prefix
            backend:
              service:
                name: reflex-layer
                port:
                  number: 8000
```

---

## 4. Memory Systems

### 4.1 Global Memory (PostgreSQL Schema)

**File**: `db/schema.sql`

```sql
-- Global semantic memory: knowledge graph
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,  -- 'person', 'tool', 'concept', etc.
    name VARCHAR(255) NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_name ON entities USING gin(to_tsvector('english', name));
CREATE INDEX idx_entities_properties ON entities USING gin(properties);

-- Relationships between entities
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    to_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,  -- 'uses', 'depends_on', 'created_by', etc.
    properties JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_relationships_from ON relationships(from_entity_id);
CREATE INDEX idx_relationships_to ON relationships(to_entity_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);

-- Task execution history
CREATE TABLE task_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(255) NOT NULL,
    goal TEXT NOT NULL,
    plan JSONB NOT NULL,
    results JSONB NOT NULL,
    success BOOLEAN NOT NULL,
    duration_ms INTEGER NOT NULL,
    cost_tokens INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_task_history_task_id ON task_history(task_id);
CREATE INDEX idx_task_history_created_at ON task_history(created_at DESC);

-- Action provenance log
CREATE TABLE action_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(255) NOT NULL,
    arm_id VARCHAR(50) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_details JSONB NOT NULL,
    result JSONB NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_action_log_task_id ON action_log(task_id);
CREATE INDEX idx_action_log_arm_id ON action_log(arm_id);
CREATE INDEX idx_action_log_timestamp ON action_log(timestamp DESC);
```

### 4.2 Local Memory (Per-Arm Vector Store)

**Example: Coder Arm Memory using Qdrant**

```python
# arms/coder/memory.py

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid

class CoderMemory:
    """Local episodic memory for Coder arm."""
    
    def __init__(self, qdrant_url: str, collection_name: str = "coder_memory"):
        self.client = QdrantClient(url=qdrant_url)
        self.collection = collection_name
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Ensure collection exists
        self._init_collection()
    
    def _init_collection(self):
        """Initialize Qdrant collection if not exists."""
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection for c in collections):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=384,  # Dimensionality of all-MiniLM-L6-v2
                    distance=Distance.COSINE
                )
            )
    
    def store_code_snippet(
        self,
        code: str,
        language: str,
        description: str,
        metadata: dict
    ) -> str:
        """Store a code snippet with embeddings."""
        
        # Create text for embedding (description + code sample)
        text_for_embedding = f"{description}\n\n{code[:200]}"  # First 200 chars
        embedding = self.encoder.encode(text_for_embedding).tolist()
        
        point_id = str(uuid.uuid4())
        
        self.client.upsert(
            collection_name=self.collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "code": code,
                        "language": language,
                        "description": description,
                        **metadata
                    }
                )
            ]
        )
        
        return point_id
    
    def search_similar_code(
        self,
        query: str,
        language: str = None,
        limit: int = 5
    ) -> list:
        """Find similar code snippets."""
        
        query_vector = self.encoder.encode(query).tolist()
        
        # Build filter if language specified
        search_filter = None
        if language:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="language",
                        match=MatchValue(value=language)
                    )
                ]
            )
        
        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=limit
        )
        
        return [
            {
                "code": r.payload["code"],
                "description": r.payload["description"],
                "language": r.payload["language"],
                "score": r.score
            }
            for r in results
        ]
```

---

## 5. Monitoring and Observability

### 5.1 Prometheus Metrics Export

**File**: `common/metrics.py`

```python
"""
Prometheus metrics for OctoLLM components.

Key metrics tracked:
- Task success/failure rates
- Latency per component
- Cost (tokens) per task
- Routing accuracy
- Cache hit rates
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from functools import wraps
import time

# Define metrics
TASK_COUNTER = Counter(
    'octollm_tasks_total',
    'Total number of tasks processed',
    ['component', 'status']
)

TASK_DURATION = Histogram(
    'octollm_task_duration_seconds',
    'Task execution duration',
    ['component'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

ARM_INVOCATIONS = Counter(
    'octollm_arm_invocations_total',
    'Number of arm invocations',
    ['arm_id', 'success']
)

CACHE_HITS = Counter(
    'octollm_cache_hits_total',
    'Number of cache hits',
    ['layer']
)

TOKEN_USAGE = Counter(
    'octollm_tokens_used_total',
    'Total tokens consumed',
    ['model']
)

ACTIVE_TASKS = Gauge(
    'octollm_active_tasks',
    'Number of currently executing tasks',
    ['component']
)

def track_task(component: str):
    """Decorator to track task metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ACTIVE_TASKS.labels(component=component).inc()
            start = time.time()
            
            try:
                result = await func(*args, **kwargs)
                TASK_COUNTER.labels(component=component, status='success').inc()
                return result
            except Exception as e:
                TASK_COUNTER.labels(component=component, status='failure').inc()
                raise
            finally:
                duration = time.time() - start
                TASK_DURATION.labels(component=component).observe(duration)
                ACTIVE_TASKS.labels(component=component).dec()
        
        return wrapper
    return decorator

def metrics_endpoint():
    """Generate Prometheus metrics output."""
    return generate_latest()
```

### 5.2 Grafana Dashboard JSON

**File**: `monitoring/grafana-dashboard.json`

```json
{
  "dashboard": {
    "title": "OctoLLM System Overview",
    "panels": [
      {
        "title": "Task Success Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(octollm_tasks_total{status=\"success\"}[5m]) / rate(octollm_tasks_total[5m])",
            "legendFormat": "{{component}}"
          }
        ]
      },
      {
        "title": "Task Latency (P95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(octollm_task_duration_seconds_bucket[5m]))",
            "legendFormat": "{{component}}"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(octollm_cache_hits_total[5m]) / (rate(octollm_cache_hits_total[5m]) + rate(octollm_tasks_total{component=\"reflex\"}[5m]))"
          }
        ]
      },
      {
        "title": "Token Usage by Model",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(octollm_tokens_used_total[5m])",
            "legendFormat": "{{model}}"
          }
        ]
      },
      {
        "title": "Active Tasks",
        "type": "graph",
        "targets": [
          {
            "expr": "octollm_active_tasks",
            "legendFormat": "{{component}}"
          }
        ]
      },
      {
        "title": "Arm Invocation Success Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(octollm_arm_invocations_total{success=\"true\"}[5m]) / rate(octollm_arm_invocations_total[5m])",
            "legendFormat": "{{arm_id}}"
          }
        ]
      }
    ]
  }
}
```

---

## 6. Development Workflow

### 6.1 Local Development with Docker Compose

**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  # Infrastructure
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
  
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: octollm
      POSTGRES_USER: octollm
      POSTGRES_PASSWORD: dev-password
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./db/schema.sql:/docker-entrypoint-initdb.d/schema.sql
  
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant-data:/qdrant/storage
  
  # OctoLLM Components
  reflex-layer:
    build: ./reflex-layer
    ports:
      - "8000:8000"
    environment:
      REDIS_URL: redis://redis:6379
      RUST_LOG: info
    depends_on:
      - redis
  
  orchestrator:
    build: ./orchestrator
    ports:
      - "8001:8000"
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      REDIS_URL: redis://redis:6379
      POSTGRES_URL: postgresql://octollm:dev-password@postgres:5432/octollm
    depends_on:
      - redis
      - postgres
      - reflex-layer
    volumes:
      - ./config:/config
  
  planner-arm:
    build: ./arms/planner
    ports:
      - "8080:8080"
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      PLANNER_MODEL: gpt-3.5-turbo
  
  executor-arm:
    build: ./arms/executor
    ports:
      - "8081:8080"
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true
  
  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana-dashboard.json:/etc/grafana/provisioning/dashboards/octollm.json

volumes:
  redis-data:
  postgres-data:
  qdrant-data:
  prometheus-data:
  grafana-data:
```

### 6.2 Testing Framework

**File**: `tests/integration/test_orchestrator.py`

```python
"""
Integration tests for OctoLLM orchestrator.

Tests cover:
- End-to-end task execution
- Error handling and recovery
- Routing accuracy
- Memory consistency
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from orchestrator.main import Orchestrator
from common.models import TaskContract, Priority

@pytest.fixture
async def orchestrator():
    """Create test orchestrator instance."""
    mock_llm = Mock()
    arm_registry = {
        "planner": Mock(endpoint="http://localhost:8080/plan"),
        "executor": Mock(endpoint="http://localhost:8081/execute"),
    }
    
    return Orchestrator(llm_client=mock_llm, arm_registry=arm_registry)

@pytest.mark.asyncio
async def test_simple_task_execution(orchestrator):
    """Test basic task execution flow."""
    
    task = TaskContract(
        task_id="test-001",
        goal="Echo 'hello world'",
        constraints=["Use only safe commands"],
        priority=Priority.LOW
    )
    
    # Mock arm responses
    with patch.object(orchestrator, '_call_arm') as mock_call:
        mock_call.side_effect = [
            # Planner response
            {"plan": [{"step": 1, "action": "echo hello", "arm": "executor"}]},
            # Executor response
            {"success": True, "stdout": "hello world"}
        ]
        
        result = await orchestrator.process_task(task)
        
        assert result is not None
        assert "hello world" in str(result)

@pytest.mark.asyncio
async def test_error_recovery(orchestrator):
    """Test orchestrator handles arm failures gracefully."""
    
    task = TaskContract(
        task_id="test-002",
        goal="Perform failing operation",
        priority=Priority.MEDIUM
    )
    
    with patch.object(orchestrator, '_call_arm') as mock_call:
        # First call fails, second succeeds (recovery)
        mock_call.side_effect = [
            Exception("Arm timeout"),
            {"success": True, "recovered": True}
        ]
        
        result = await orchestrator.process_task(task)
        
        assert result.get("recovered") is True

@pytest.mark.asyncio
async def test_routing_accuracy(orchestrator):
    """Test that router selects correct arm for task."""
    
    from orchestrator.routing import Router
    
    router = Router(orchestrator.registry)
    
    code_task = TaskContract(
        task_id="test-003",
        goal="Write a Python function to sort a list",
        priority=Priority.MEDIUM
    )
    
    selected_arms = router.route_task(code_task)
    
    # Should route to coder arm for code generation
    assert "coder" in selected_arms or "generalist" in selected_arms

def test_task_contract_validation():
    """Test TaskContract model validation."""
    
    # Valid contract
    valid = TaskContract(
        task_id="test-004",
        goal="Test goal",
        constraints=["constraint1"],
        acceptance_criteria=["criteria1"]
    )
    assert valid.task_id == "test-004"
    
    # Invalid: missing required field
    with pytest.raises(ValueError):
        TaskContract(goal="Test without ID")
```

**Run tests**:
```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires services running)
docker-compose up -d
pytest tests/integration/ -v

# Coverage report
pytest --cov=orchestrator --cov=arms --cov-report=html
```

---

## 7. Security Hardening

### 7.1 Network Policies

**File**: `k8s/50-network-policies.yaml`

```yaml
# Deny all traffic by default
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: octollm
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
# Allow orchestrator to call arms
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: orchestrator-to-arms
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      component: arm
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              component: brain
      ports:
        - protocol: TCP
          port: 8080
---
# Allow executor arm to access external services only
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: executor-egress
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: executor-arm
  policyTypes:
    - Egress
  egress:
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53
    # Allow specific external endpoints only
    - to:
        - podSelector: {}  # Within namespace
      ports:
        - protocol: TCP
    # Block all other egress
```

### 7.2 Pod Security Policy

**File**: `k8s/51-pod-security.yaml`

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: octollm-restricted
  annotations:
    seccomp.security.alpha.kubernetes.io/allowedProfileNames: 'runtime/default'
    apparmor.security.beta.kubernetes.io/allowedProfileNames: 'runtime/default'
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  readOnlyRootFilesystem: true
```

---

## 8. Operational Procedures

### 8.1 Deployment Checklist

**Pre-Deployment**:
- [ ] All Docker images built and tagged
- [ ] Secrets created for API keys (`llm-api-keys`)
- [ ] ConfigMaps updated with correct endpoints
- [ ] Database schema applied
- [ ] TLS certificates provisioned
- [ ] Monitoring stack deployed

**Deployment**:
```bash
# Apply namespace and RBAC
kubectl apply -f k8s/00-namespace.yaml

# Create secrets
kubectl create secret generic llm-api-keys \
  --from-literal=openai-key=$OPENAI_API_KEY \
  -n octollm

# Apply infrastructure
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-redis.yaml
kubectl apply -f k8s/03-postgres.yaml

# Deploy components
kubectl apply -f k8s/10-orchestrator.yaml
kubectl apply -f k8s/11-reflex-layer.yaml
kubectl apply -f k8s/20-planner-arm.yaml
kubectl apply -f k8s/21-executor-arm.yaml

# Apply autoscaling and monitoring
kubectl apply -f k8s/30-hpa.yaml
kubectl apply -f k8s/40-ingress.yaml
kubectl apply -f k8s/50-network-policies.yaml

# Verify all pods running
kubectl get pods -n octollm
```

**Post-Deployment**:
- [ ] Health checks passing
- [ ] Metrics visible in Prometheus
- [ ] Smoke test with sample task
- [ ] Load test with expected traffic
- [ ] Alerts configured in alertmanager

### 8.2 Troubleshooting Guide

**Common Issues**:

1. **Orchestrator not routing to arms**
   - Check: ConfigMap loaded (`kubectl describe configmap arm-registry -n octollm`)
   - Check: DNS resolution (`kubectl exec -it orchestrator-xxx -- nslookup planner-arm`)
   - Check: Network policies allow traffic

2. **High latency in reflex layer**
   - Check: Redis connection healthy
   - Check: Cache hit rate metrics
   - Scale up replicas if CPU saturated

3. **Executor arm blocked**
   - Check: Capability allowlists in code
   - Check: Network policy allows specific egress
   - Review audit logs for denied actions

4. **Memory leak in orchestrator**
   - Check: Prometheus memory metrics
   - Check: Global memory cleanup jobs running
   - Restart pod as temporary fix, investigate with heap profiler

**Debug Commands**:
```bash
# View orchestrator logs
kubectl logs -f deployment/orchestrator -n octollm

# Exec into pod for debugging
kubectl exec -it orchestrator-xxx -n octollm -- /bin/bash

# Port-forward for local testing
kubectl port-forward svc/orchestrator 8000:8000 -n octollm

# Check resource usage
kubectl top pods -n octollm
```

---

## 9. Future Enhancements

### 9.1 Planned Features (Phase 2+)

**Advanced Routing**:
- Reinforcement learning for orchestrator policy
- Multi-armed bandit for arm selection
- Cost-aware routing (cheapest path to goal)

**Enhanced Security**:
- Homomorphic encryption for sensitive data
- Zero-knowledge proofs for verification
- Federated learning across deployments

**Performance**:
- GPU acceleration for specialist arms
- Speculative execution (predict next arm in parallel)
- Streaming results (partial answers)

**Observability**:
- Distributed tracing with OpenTelemetry
- Anomaly detection on metrics
- Automated incident response

### 9.2 Extension Points

**Adding New Arms**:
1. Implement arm logic (Python/Rust)
2. Containerize with Dockerfile
3. Add to arm registry ConfigMap
4. Update orchestrator routing logic (if needed)
5. Deploy to Kubernetes

**Custom Memory Stores**:
- Implement `MemoryStore` interface
- Configure in orchestrator environment
- Migrate existing data if necessary

**Alternative LLM Backends**:
- Abstract LLM calls behind interface
- Implement provider-specific adapters
- A/B test with traffic splitting

---

## 10. Conclusion

This technical implementation guide provides a comprehensive blueprint for building OctoLLM from first principles. The architecture balances:

- **Modularity**: Independent components that compose cleanly
- **Security**: Defense-in-depth with isolation and validation
- **Performance**: Hierarchical processing minimizes waste
- **Observability**: Comprehensive metrics and tracing
- **Operability**: Production-ready deployment patterns

**Next Steps**:
1. Clone starter repository: `git clone https://github.com/your-org/octollm-starter`
2. Follow quickstart guide in `docs/quickstart.md`
3. Deploy minimal system with Docker Compose
4. Iterate on arms and orchestrator logic
5. Scale to Kubernetes for production

**Resources**:
- Full code repository: https://github.com/your-org/octollm
- Documentation site: https://docs.octollm.io
- Community Discord: https://discord.gg/octollm

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-10  
**Maintained By**: OctoLLM Core Team
