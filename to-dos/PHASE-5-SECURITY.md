# Phase 5: Security Hardening

**Status**: Not Started
**Duration**: 8-10 weeks
**Team Size**: 3-4 engineers (2 security specialists, 1 DevOps, 1 Python/Rust)
**Prerequisites**: Phase 2 complete (all arms deployed)
**Start Date**: TBD
**Target Completion**: TBD

---

## Overview

Phase 5 implements comprehensive security hardening across all system layers, establishing defense-in-depth with capability-based access control, container sandboxing, PII protection, security testing automation, and comprehensive audit logging.

**Key Deliverables**:
1. Capability System - JWT-based time-limited permissions with automatic rotation
2. Container Sandboxing - gVisor, seccomp profiles, resource limits, network policies
3. PII Protection - Multi-layer detection (regex + NER), redaction, differential privacy
4. Security Testing - SAST, DAST, dependency scanning, penetration testing automation
5. Audit Logging - Immutable provenance tracking, compliance reporting (GDPR, CCPA, SOC 2)

**Success Criteria**:
- ✅ Zero high-severity vulnerabilities in production
- ✅ PII detection >99% accuracy (F1 score)
- ✅ Container escapes blocked (100% in testing)
- ✅ All API calls authenticated and authorized
- ✅ Audit logs immutable and complete (100% coverage)
- ✅ GDPR/CCPA compliance verified
- ✅ Penetration test passed with no critical findings

**Reference**: `docs/doc_phases/PHASE-5-COMPLETE-SPECIFICATIONS.md` (12,500+ lines)

---

## Sprint 5.1: Capability System [Week 23-24]

**Duration**: 2 weeks
**Team**: 2 engineers (1 security specialist, 1 Python)
**Prerequisites**: Phase 2 complete (all arms deployed)
**Priority**: CRITICAL

### Sprint Goals

- Implement JWT-based capability tokens with time-limited scopes
- Create capability validation middleware for all arms
- Set up automatic token rotation and revocation
- Implement least-privilege principle for all operations
- Audit all capability grants and usage
- Document capability design patterns

### Architecture Decisions

**Token Format**: JWT with custom claims for capabilities
**Signing Algorithm**: RS256 (asymmetric) for key rotation
**Token Lifetime**: 15 minutes default, 1 hour maximum
**Storage**: Redis for active tokens, PostgreSQL for audit trail
**Revocation Strategy**: Token blocklist + short TTL

### Tasks

#### Capability Token Generation (8 hours)

- [ ] **Design Capability Schema** (2 hours)
  - Define capability types (read, write, execute, admin)
  - Define resource scopes (task_id, arm_id, global)
  - Define constraint types (time_limit, cost_limit, data_limit)
  - Code example:
    ```python
    # orchestrator/auth/capabilities.py
    from typing import List, Optional, Dict, Any
    from datetime import datetime, timedelta
    from pydantic import BaseModel, Field
    import jwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    class CapabilityScope(BaseModel):
        """Defines what resources a capability grants access to."""
        resource_type: str  # "task", "arm", "memory", "global"
        resource_id: Optional[str] = None  # Specific ID or "*" for all
        actions: List[str]  # ["read", "write", "execute", "delete"]

    class CapabilityConstraints(BaseModel):
        """Constraints on capability usage."""
        max_cost_tokens: Optional[int] = None
        max_execution_time_seconds: Optional[int] = None
        allowed_tools: Optional[List[str]] = None
        blocked_hosts: List[str] = Field(default_factory=list)
        allowed_hosts: Optional[List[str]] = None
        max_output_size_bytes: Optional[int] = None

    class CapabilityToken(BaseModel):
        """JWT payload for capability tokens."""
        sub: str  # Subject (arm_id or user_id)
        iss: str = "octollm-orchestrator"  # Issuer
        aud: str  # Audience (target arm or service)
        exp: datetime  # Expiration time
        nbf: datetime  # Not before time
        iat: datetime  # Issued at time
        jti: str  # JWT ID (unique token identifier)
        scopes: List[CapabilityScope]
        constraints: CapabilityConstraints
        task_id: Optional[str] = None  # Associated task
        parent_token_id: Optional[str] = None  # Token delegation chain

    class CapabilityManager:
        """Manages capability token lifecycle."""

        def __init__(
            self,
            private_key_path: str,
            public_key_path: str,
            redis_client: Redis,
            db_session: AsyncSession
        ):
            """Initialize capability manager with RSA keys."""
            self.redis = redis_client
            self.db = db_session

            # Load RSA keys
            with open(private_key_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )

            with open(public_key_path, "rb") as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )

        async def issue_token(
            self,
            subject: str,
            audience: str,
            scopes: List[CapabilityScope],
            constraints: CapabilityConstraints,
            lifetime_seconds: int = 900,  # 15 minutes default
            task_id: Optional[str] = None
        ) -> str:
            """Issue a new capability token."""
            import uuid

            now = datetime.utcnow()
            token_id = str(uuid.uuid4())

            payload = CapabilityToken(
                sub=subject,
                aud=audience,
                exp=now + timedelta(seconds=lifetime_seconds),
                nbf=now,
                iat=now,
                jti=token_id,
                scopes=scopes,
                constraints=constraints,
                task_id=task_id
            )

            # Sign token
            token = jwt.encode(
                payload.dict(),
                self.private_key,
                algorithm="RS256"
            )

            # Store in Redis for revocation checks
            await self.redis.setex(
                f"capability:{token_id}",
                lifetime_seconds,
                token
            )

            # Audit log
            await self._log_token_issuance(payload)

            return token

        async def validate_token(
            self,
            token: str,
            required_scope: CapabilityScope
        ) -> CapabilityToken:
            """Validate token and check if it grants required scope."""
            try:
                # Decode and verify signature
                payload = jwt.decode(
                    token,
                    self.public_key,
                    algorithms=["RS256"],
                    options={"verify_exp": True}
                )

                capability = CapabilityToken(**payload)

                # Check if token is revoked
                token_exists = await self.redis.exists(f"capability:{capability.jti}")
                if not token_exists:
                    raise ValueError("Token has been revoked")

                # Check if token grants required scope
                if not self._has_scope(capability, required_scope):
                    raise PermissionError(f"Token does not grant required scope: {required_scope}")

                # Audit log
                await self._log_token_usage(capability, required_scope)

                return capability

            except jwt.ExpiredSignatureError:
                raise ValueError("Token has expired")
            except jwt.InvalidTokenError as e:
                raise ValueError(f"Invalid token: {e}")

        def _has_scope(
            self,
            capability: CapabilityToken,
            required_scope: CapabilityScope
        ) -> bool:
            """Check if capability grants required scope."""
            for scope in capability.scopes:
                # Check resource type matches
                if scope.resource_type != required_scope.resource_type:
                    continue

                # Check resource ID matches (or is wildcard)
                if scope.resource_id not in (required_scope.resource_id, "*"):
                    continue

                # Check all required actions are granted
                if all(action in scope.actions for action in required_scope.actions):
                    return True

            return False

        async def revoke_token(self, token_id: str):
            """Revoke a token before expiration."""
            await self.redis.delete(f"capability:{token_id}")
            await self._log_token_revocation(token_id)

        async def _log_token_issuance(self, capability: CapabilityToken):
            """Log token issuance to database."""
            # Implementation: Insert into audit_logs table
            pass

        async def _log_token_usage(self, capability: CapabilityToken, scope: CapabilityScope):
            """Log token usage to database."""
            # Implementation: Insert into audit_logs table
            pass

        async def _log_token_revocation(self, token_id: str):
            """Log token revocation to database."""
            # Implementation: Insert into audit_logs table
            pass
    ```
  - Files to create: `orchestrator/auth/capabilities.py`

- [ ] **Generate RSA Key Pair** (1 hour)
  - Create key generation script
  - Store in Kubernetes secrets
  - Implement key rotation strategy
  - Code example:
    ```python
    # scripts/generate_capability_keys.py
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    import os

    def generate_rsa_keys(key_size: int = 4096):
        """Generate RSA key pair for capability tokens."""

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )

        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Generate public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # Write to files
        os.makedirs("keys", exist_ok=True)

        with open("keys/capability_private_key.pem", "wb") as f:
            f.write(private_pem)
        os.chmod("keys/capability_private_key.pem", 0o600)

        with open("keys/capability_public_key.pem", "wb") as f:
            f.write(public_pem)

        print("Generated RSA keys:")
        print("  Private: keys/capability_private_key.pem")
        print("  Public: keys/capability_public_key.pem")
        print("\nAdd to Kubernetes secrets:")
        print("  kubectl create secret generic capability-keys \\")
        print("    --from-file=private=keys/capability_private_key.pem \\")
        print("    --from-file=public=keys/capability_public_key.pem \\")
        print("    -n octollm")

    if __name__ == "__main__":
        generate_rsa_keys()
    ```
  - Files to create: `scripts/generate_capability_keys.py`

- [ ] **Implement Token Refresh Endpoint** (2 hours)
  - FastAPI endpoint for token renewal
  - Validate existing token before refresh
  - Prevent token chaining abuse
  - Code example:
    ```python
    # orchestrator/api/auth.py
    from fastapi import APIRouter, Depends, HTTPException, Header
    from typing import Optional

    router = APIRouter(prefix="/auth", tags=["authentication"])

    async def get_capability_manager() -> CapabilityManager:
        """Dependency injection for capability manager."""
        # Implementation: Get from app state
        pass

    @router.post("/token/refresh", response_model=Dict[str, Any])
    async def refresh_token(
        authorization: str = Header(...),
        manager: CapabilityManager = Depends(get_capability_manager)
    ) -> Dict[str, Any]:
        """Refresh an existing capability token.

        Args:
            authorization: Bearer token to refresh

        Returns:
            New token with same scopes and constraints

        Raises:
            HTTPException: If token is invalid or expired
        """
        # Extract token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")

        old_token = authorization[7:]

        try:
            # Validate old token (this also checks expiration)
            capability = await manager.validate_token(
                old_token,
                CapabilityScope(resource_type="global", actions=["refresh"])
            )
        except ValueError as e:
            # Token expired - allow refresh if within grace period (5 minutes)
            try:
                payload = jwt.decode(
                    old_token,
                    manager.public_key,
                    algorithms=["RS256"],
                    options={"verify_exp": False}  # Skip expiration check
                )
                capability = CapabilityToken(**payload)

                # Check if within grace period
                grace_period_seconds = 300  # 5 minutes
                if (datetime.utcnow() - capability.exp).total_seconds() > grace_period_seconds:
                    raise HTTPException(status_code=401, detail="Token expired beyond grace period")
            except Exception:
                raise HTTPException(status_code=401, detail=str(e))
        except PermissionError:
            raise HTTPException(status_code=403, detail="Token does not have refresh permission")

        # Issue new token with same scopes
        new_token = await manager.issue_token(
            subject=capability.sub,
            audience=capability.aud,
            scopes=capability.scopes,
            constraints=capability.constraints,
            task_id=capability.task_id
        )

        # Revoke old token
        await manager.revoke_token(capability.jti)

        return {
            "access_token": new_token,
            "token_type": "Bearer",
            "expires_in": 900  # 15 minutes
        }
    ```
  - Files to create: `orchestrator/api/auth.py`

- [ ] **Create Capability Middleware** (3 hours)
  - FastAPI middleware for automatic validation
  - Extract and validate tokens from headers
  - Inject validated capability into request state
  - Code example:
    ```python
    # orchestrator/middleware/auth.py
    from fastapi import Request, HTTPException
    from starlette.middleware.base import BaseHTTPMiddleware
    from typing import Callable

    class CapabilityMiddleware(BaseHTTPMiddleware):
        """Middleware to validate capability tokens on all requests."""

        def __init__(
            self,
            app,
            capability_manager: CapabilityManager,
            public_paths: List[str] = None
        ):
            super().__init__(app)
            self.manager = capability_manager
            self.public_paths = public_paths or ["/health", "/metrics", "/docs", "/openapi.json"]

        async def dispatch(self, request: Request, call_next: Callable):
            """Validate capability token for protected endpoints."""

            # Skip authentication for public paths
            if request.url.path in self.public_paths:
                return await call_next(request)

            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

            token = auth_header[7:]

            # Determine required scope based on request
            required_scope = self._get_required_scope(request)

            # Validate token
            try:
                capability = await self.manager.validate_token(token, required_scope)
            except ValueError as e:
                raise HTTPException(status_code=401, detail=str(e))
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))

            # Inject capability into request state
            request.state.capability = capability

            # Continue processing request
            response = await call_next(request)

            return response

        def _get_required_scope(self, request: Request) -> CapabilityScope:
            """Determine required scope based on HTTP method and path."""

            # Parse path to extract resource type and ID
            path_parts = request.url.path.strip("/").split("/")

            if len(path_parts) >= 2 and path_parts[0] == "tasks":
                resource_type = "task"
                resource_id = path_parts[1] if len(path_parts) > 1 else None
            elif len(path_parts) >= 2 and path_parts[0] == "arms":
                resource_type = "arm"
                resource_id = path_parts[1] if len(path_parts) > 1 else None
            else:
                resource_type = "global"
                resource_id = None

            # Determine actions based on HTTP method
            method_to_actions = {
                "GET": ["read"],
                "POST": ["write"],
                "PUT": ["write"],
                "PATCH": ["write"],
                "DELETE": ["delete"]
            }
            actions = method_to_actions.get(request.method, ["read"])

            return CapabilityScope(
                resource_type=resource_type,
                resource_id=resource_id,
                actions=actions
            )
    ```
  - Files to create: `orchestrator/middleware/auth.py`

#### Arm Integration (6 hours)

- [ ] **Add Capability Validation to All Arms** (4 hours)
  - Planner Arm: Validate planning capabilities
  - Executor Arm: Validate execution capabilities with tool constraints
  - Coder Arm: Validate code generation capabilities
  - Judge Arm: Validate validation capabilities
  - Safety Guardian Arm: Validate PII detection capabilities
  - Retriever Arm: Validate search capabilities
  - Code example (Executor Arm):
    ```rust
    // arms/executor/src/auth.rs
    use jsonwebtoken::{decode, DecodingKey, Validation, Algorithm};
    use serde::{Deserialize, Serialize};
    use chrono::{DateTime, Utc};
    use std::collections::HashSet;

    #[derive(Debug, Serialize, Deserialize)]
    pub struct CapabilityScope {
        pub resource_type: String,
        pub resource_id: Option<String>,
        pub actions: Vec<String>,
    }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct CapabilityConstraints {
        pub max_execution_time_seconds: Option<u64>,
        pub allowed_tools: Option<Vec<String>>,
        pub blocked_hosts: Vec<String>,
        pub allowed_hosts: Option<Vec<String>>,
    }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct CapabilityToken {
        pub sub: String,
        pub aud: String,
        pub exp: i64,
        pub jti: String,
        pub scopes: Vec<CapabilityScope>,
        pub constraints: CapabilityConstraints,
        pub task_id: Option<String>,
    }

    pub struct CapabilityValidator {
        public_key: DecodingKey,
    }

    impl CapabilityValidator {
        pub fn new(public_key_pem: &str) -> Result<Self, Box<dyn std::error::Error>> {
            let public_key = DecodingKey::from_rsa_pem(public_key_pem.as_bytes())?;
            Ok(Self { public_key })
        }

        pub fn validate_token(
            &self,
            token: &str,
            required_scope: &CapabilityScope,
        ) -> Result<CapabilityToken, Box<dyn std::error::Error>> {
            // Decode and verify token
            let mut validation = Validation::new(Algorithm::RS256);
            validation.set_audience(&["executor-arm"]);

            let token_data = decode::<CapabilityToken>(
                token,
                &self.public_key,
                &validation,
            )?;

            let capability = token_data.claims;

            // Check if token grants required scope
            if !self.has_scope(&capability, required_scope) {
                return Err("Token does not grant required scope".into());
            }

            Ok(capability)
        }

        fn has_scope(
            &self,
            capability: &CapabilityToken,
            required_scope: &CapabilityScope,
        ) -> bool {
            for scope in &capability.scopes {
                // Check resource type matches
                if scope.resource_type != required_scope.resource_type {
                    continue;
                }

                // Check resource ID matches (or is wildcard)
                let resource_id_match = match (&scope.resource_id, &required_scope.resource_id) {
                    (Some(id1), Some(id2)) => id1 == id2 || id1 == "*",
                    (Some(id), None) => id == "*",
                    (None, _) => false,
                };

                if !resource_id_match {
                    continue;
                }

                // Check all required actions are granted
                let required_actions: HashSet<_> = required_scope.actions.iter().collect();
                let granted_actions: HashSet<_> = scope.actions.iter().collect();

                if required_actions.is_subset(&granted_actions) {
                    return true;
                }
            }

            false
        }

        pub fn validate_tool_execution(
            &self,
            capability: &CapabilityToken,
            tool_name: &str,
        ) -> Result<(), Box<dyn std::error::Error>> {
            // Check if tool is allowed
            if let Some(allowed_tools) = &capability.constraints.allowed_tools {
                if !allowed_tools.contains(&tool_name.to_string()) {
                    return Err(format!("Tool '{}' not allowed by capability", tool_name).into());
                }
            }

            Ok(())
        }

        pub fn validate_host_access(
            &self,
            capability: &CapabilityToken,
            host: &str,
        ) -> Result<(), Box<dyn std::error::Error>> {
            // Check blocked hosts
            if capability.constraints.blocked_hosts.iter().any(|h| h == host) {
                return Err(format!("Host '{}' is blocked", host).into());
            }

            // Check allowed hosts (if specified)
            if let Some(allowed_hosts) = &capability.constraints.allowed_hosts {
                if !allowed_hosts.iter().any(|h| h == host) {
                    return Err(format!("Host '{}' not in allowed list", host).into());
                }
            }

            Ok(())
        }
    }

    // Integration with Actix-web
    use actix_web::{
        dev::{forward_ready, Service, ServiceRequest, ServiceResponse, Transform},
        Error, HttpMessage, HttpResponse,
    };
    use futures::future::LocalBoxFuture;
    use std::rc::Rc;

    pub struct CapabilityAuth {
        validator: Rc<CapabilityValidator>,
    }

    impl CapabilityAuth {
        pub fn new(public_key_pem: &str) -> Result<Self, Box<dyn std::error::Error>> {
            let validator = CapabilityValidator::new(public_key_pem)?;
            Ok(Self {
                validator: Rc::new(validator),
            })
        }
    }

    impl<S, B> Transform<S, ServiceRequest> for CapabilityAuth
    where
        S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
        S::Future: 'static,
        B: 'static,
    {
        type Response = ServiceResponse<B>;
        type Error = Error;
        type InitError = ();
        type Transform = CapabilityAuthMiddleware<S>;
        type Future = std::future::Ready<Result<Self::Transform, Self::InitError>>;

        fn new_transform(&self, service: S) -> Self::Future {
            std::future::ready(Ok(CapabilityAuthMiddleware {
                service: Rc::new(service),
                validator: self.validator.clone(),
            }))
        }
    }

    pub struct CapabilityAuthMiddleware<S> {
        service: Rc<S>,
        validator: Rc<CapabilityValidator>,
    }

    impl<S, B> Service<ServiceRequest> for CapabilityAuthMiddleware<S>
    where
        S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
        S::Future: 'static,
        B: 'static,
    {
        type Response = ServiceResponse<B>;
        type Error = Error;
        type Future = LocalBoxFuture<'static, Result<Self::Response, Self::Error>>;

        forward_ready!(service);

        fn call(&self, req: ServiceRequest) -> Self::Future {
            let validator = self.validator.clone();
            let service = self.service.clone();

            Box::pin(async move {
                // Extract token from Authorization header
                let auth_header = req.headers().get("Authorization");

                let token = if let Some(value) = auth_header {
                    let auth_str = value.to_str().map_err(|_| {
                        actix_web::error::ErrorUnauthorized("Invalid authorization header")
                    })?;

                    if !auth_str.starts_with("Bearer ") {
                        return Err(actix_web::error::ErrorUnauthorized("Invalid authorization format"));
                    }

                    &auth_str[7..]
                } else {
                    return Err(actix_web::error::ErrorUnauthorized("Missing authorization header"));
                };

                // Validate token
                let required_scope = CapabilityScope {
                    resource_type: "arm".to_string(),
                    resource_id: Some("executor".to_string()),
                    actions: vec!["execute".to_string()],
                };

                let capability = validator.validate_token(token, &required_scope)
                    .map_err(|e| actix_web::error::ErrorForbidden(e.to_string()))?;

                // Store capability in request extensions
                req.extensions_mut().insert(capability);

                // Continue processing
                service.call(req).await
            })
        }
    }
    ```
  - Files to update: `arms/executor/src/auth.rs`, `arms/executor/src/main.rs`

- [ ] **Test Capability Enforcement** (2 hours)
  - Unit tests for token validation
  - Integration tests for denied access
  - Test token expiration handling
  - Test constraint enforcement
  - Code example:
    ```python
    # tests/test_capabilities.py
    import pytest
    from datetime import datetime, timedelta
    import jwt

    @pytest.mark.asyncio
    async def test_token_validation_success(capability_manager):
        """Test successful token validation."""
        scopes = [
            CapabilityScope(
                resource_type="task",
                resource_id="task-123",
                actions=["read", "write"]
            )
        ]
        constraints = CapabilityConstraints(max_cost_tokens=1000)

        token = await capability_manager.issue_token(
            subject="planner-arm",
            audience="orchestrator",
            scopes=scopes,
            constraints=constraints
        )

        required_scope = CapabilityScope(
            resource_type="task",
            resource_id="task-123",
            actions=["read"]
        )

        validated = await capability_manager.validate_token(token, required_scope)
        assert validated.sub == "planner-arm"

    @pytest.mark.asyncio
    async def test_token_validation_insufficient_scope(capability_manager):
        """Test token validation fails with insufficient scope."""
        scopes = [
            CapabilityScope(
                resource_type="task",
                resource_id="task-123",
                actions=["read"]
            )
        ]
        constraints = CapabilityConstraints()

        token = await capability_manager.issue_token(
            subject="planner-arm",
            audience="orchestrator",
            scopes=scopes,
            constraints=constraints
        )

        required_scope = CapabilityScope(
            resource_type="task",
            resource_id="task-123",
            actions=["write"]  # Not granted
        )

        with pytest.raises(PermissionError):
            await capability_manager.validate_token(token, required_scope)

    @pytest.mark.asyncio
    async def test_token_expiration(capability_manager):
        """Test token expires after TTL."""
        scopes = [CapabilityScope(resource_type="global", actions=["read"])]
        constraints = CapabilityConstraints()

        # Issue token with 1 second lifetime
        token = await capability_manager.issue_token(
            subject="test",
            audience="test",
            scopes=scopes,
            constraints=constraints,
            lifetime_seconds=1
        )

        # Wait for expiration
        await asyncio.sleep(2)

        required_scope = CapabilityScope(resource_type="global", actions=["read"])
        with pytest.raises(ValueError, match="expired"):
            await capability_manager.validate_token(token, required_scope)

    @pytest.mark.asyncio
    async def test_token_revocation(capability_manager):
        """Test token can be revoked."""
        scopes = [CapabilityScope(resource_type="global", actions=["read"])]
        constraints = CapabilityConstraints()

        token = await capability_manager.issue_token(
            subject="test",
            audience="test",
            scopes=scopes,
            constraints=constraints
        )

        # Decode to get token ID
        payload = jwt.decode(
            token,
            capability_manager.public_key,
            algorithms=["RS256"],
            options={"verify_exp": False}
        )

        # Revoke token
        await capability_manager.revoke_token(payload["jti"])

        # Validation should fail
        required_scope = CapabilityScope(resource_type="global", actions=["read"])
        with pytest.raises(ValueError, match="revoked"):
            await capability_manager.validate_token(token, required_scope)
    ```
  - Files to create: `tests/test_capabilities.py`

#### Documentation and Deployment (2 hours)

- [ ] **Document Capability Patterns** (1 hour)
  - Least-privilege examples
  - Token delegation patterns
  - Constraint design guidelines
  - Files to create: `docs/security/capability-patterns.md`

- [ ] **Update Kubernetes Deployments** (1 hour)
  - Mount RSA public key in all arm pods
  - Environment variables for key paths
  - Secret rotation procedures
  - Code example:
    ```yaml
    # k8s/arms/executor-deployment.yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: executor-arm
      namespace: octollm
    spec:
      replicas: 3
      template:
        spec:
          containers:
          - name: executor-arm
            image: octollm/executor-arm:latest
            env:
            - name: CAPABILITY_PUBLIC_KEY_PATH
              value: /etc/octollm/keys/capability_public_key.pem
            volumeMounts:
            - name: capability-keys
              mountPath: /etc/octollm/keys
              readOnly: true
          volumes:
          - name: capability-keys
            secret:
              secretName: capability-keys
              items:
              - key: public
                path: capability_public_key.pem
    ```
  - Files to update: All arm deployment YAML files

### Testing Requirements

#### Unit Tests
- [ ] Token generation and validation (20 test cases)
- [ ] Scope matching logic (15 test cases)
- [ ] Constraint enforcement (10 test cases)
- [ ] Key rotation (5 test cases)

#### Integration Tests
- [ ] End-to-end token flow (orchestrator → arm → validation)
- [ ] Token refresh workflow
- [ ] Multi-arm delegation chains
- [ ] Revocation propagation

#### Security Tests
- [ ] Token forgery attempts (invalid signatures)
- [ ] Scope escalation attempts
- [ ] Expired token usage
- [ ] Replay attack prevention

### Documentation Deliverables

- [ ] Capability system architecture diagram (Mermaid)
- [ ] Token lifecycle documentation
- [ ] Scope design guidelines
- [ ] Key rotation runbook
- [ ] Troubleshooting guide (common auth failures)

### Success Criteria

- [ ] All API endpoints require valid capability tokens
- [ ] Token validation latency <5ms (P95)
- [ ] Zero privilege escalation vulnerabilities in testing
- [ ] Audit logs capture 100% of token operations
- [ ] Key rotation procedure tested and documented

### Common Pitfalls

1. **Clock Skew**: Use NTP synchronization across all nodes to prevent token expiration issues
2. **Key Rotation Downtime**: Implement graceful key rotation with overlapping validity periods
3. **Token Size**: Keep scopes minimal to avoid large JWT payloads (>1KB impacts performance)
4. **Revocation Lag**: Redis eviction policies can cause revoked tokens to persist—use explicit TTL checks
5. **Constraint Bypass**: Validate constraints at execution time, not just at token issuance

### Estimated Effort

- Development: 16 hours
- Testing: 4 hours
- Documentation: 2 hours
- **Total**: 22 hours (~1 week for 2 engineers)

### Dependencies

- **Prerequisites**: Redis cluster, PostgreSQL for audit logs
- **Blocking**: None
- **Blocked By**: Sprint 5.1 must complete before Sprint 5.2 (sandboxing needs capability validation)

---

## Sprint 5.2: Container Sandboxing [Week 25-26]

**Duration**: 2 weeks
**Team**: 2 engineers (1 security specialist, 1 DevOps)
**Prerequisites**: Sprint 5.1 complete (capability system)
**Priority**: CRITICAL

### Sprint Goals

- Implement gVisor runtime for Executor Arm containers
- Create seccomp profiles for syscall filtering
- Set up resource limits (CPU, memory, network)
- Implement network policies for egress control
- Test container escape prevention
- Document sandbox configuration

### Architecture Decisions

**Container Runtime**: gVisor (runsc) for syscall-level isolation
**Seccomp Mode**: Allowlist-based (deny all, allow specific syscalls)
**Resource Limits**: cgroups v2 with memory, CPU, and I/O constraints
**Network Policy**: Default deny egress, explicit allow for required services
**Storage**: Ephemeral volumes only (no persistent data in sandboxes)

### Tasks

#### gVisor Integration (10 hours)

- [ ] **Install gVisor Runtime** (2 hours)
  - Install runsc on Kubernetes nodes
  - Configure containerd to use runsc
  - Test runtime with sample workload
  - Code example:
    ```bash
    # Install gVisor on Kubernetes nodes
    # scripts/install-gvisor.sh
    #!/bin/bash
    set -e

    echo "Installing gVisor runtime..."

    # Download runsc binary
    ARCH=$(uname -m)
    URL=https://storage.googleapis.com/gvisor/releases/release/latest/${ARCH}

    wget ${URL}/runsc ${URL}/runsc.sha512
    sha512sum -c runsc.sha512
    rm -f runsc.sha512

    # Install runsc
    chmod +x runsc
    sudo mv runsc /usr/local/bin/

    # Configure containerd
    cat <<EOF | sudo tee /etc/containerd/config.toml
    version = 2
    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc]
      runtime_type = "io.containerd.runsc.v1"
    EOF

    # Restart containerd
    sudo systemctl restart containerd

    echo "gVisor runtime installed successfully"
    ```
  - Files to create: `scripts/install-gvisor.sh`

- [ ] **Create RuntimeClass for gVisor** (1 hour)
  - Define RuntimeClass resource
  - Configure platform-specific settings
  - Code example:
    ```yaml
    # k8s/security/gvisor-runtimeclass.yaml
    apiVersion: node.k8s.io/v1
    kind: RuntimeClass
    metadata:
      name: gvisor
    handler: runsc
    scheduling:
      nodeSelector:
        gvisor: "enabled"
      tolerations:
      - key: gvisor
        operator: Exists
        effect: NoSchedule
    ```
  - Files to create: `k8s/security/gvisor-runtimeclass.yaml`

- [ ] **Update Executor Arm Pod Spec** (2 hours)
  - Add runtimeClassName to pod spec
  - Configure security context
  - Test execution under gVisor
  - Code example:
    ```yaml
    # k8s/arms/executor-deployment.yaml (updated)
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: executor-arm
      namespace: octollm
    spec:
      replicas: 3
      template:
        spec:
          runtimeClassName: gvisor  # Use gVisor runtime
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            fsGroup: 1000
            seccompProfile:
              type: Localhost
              localhostProfile: executor-arm.json
          containers:
          - name: executor-arm
            image: octollm/executor-arm:latest
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
            resources:
              limits:
                memory: "2Gi"
                cpu: "1000m"
                ephemeral-storage: "1Gi"
              requests:
                memory: "1Gi"
                cpu: "500m"
                ephemeral-storage: "500Mi"
            volumeMounts:
            - name: tmp
              mountPath: /tmp
          volumes:
          - name: tmp
            emptyDir:
              sizeLimit: 500Mi
    ```
  - Files to update: `k8s/arms/executor-deployment.yaml`

- [ ] **Benchmark gVisor Performance** (3 hours)
  - Measure syscall overhead
  - Compare runc vs runsc latency
  - Optimize for common workloads
  - Code example:
    ```python
    # scripts/benchmark_gvisor.py
    import subprocess
    import time
    import statistics
    from typing import List, Dict

    def benchmark_runtime(runtime: str, iterations: int = 100) -> Dict[str, float]:
        """Benchmark container runtime performance."""

        results = {
            "startup_times": [],
            "syscall_times": [],
            "network_times": []
        }

        for i in range(iterations):
            # Test 1: Container startup time
            start = time.time()
            subprocess.run([
                "kubectl", "run", f"test-{runtime}-{i}",
                "--image=alpine:latest",
                "--restart=Never",
                "--rm",
                f"--overrides={{\"spec\":{{\"runtimeClassName\":\"{runtime}\"}}}}",
                "--", "echo", "hello"
            ], check=True, capture_output=True)
            startup_time = time.time() - start
            results["startup_times"].append(startup_time)

            time.sleep(0.5)  # Avoid rate limiting

        # Calculate statistics
        return {
            "startup_p50": statistics.median(results["startup_times"]),
            "startup_p95": statistics.quantiles(results["startup_times"], n=20)[18],
            "startup_p99": statistics.quantiles(results["startup_times"], n=100)[98],
        }

    if __name__ == "__main__":
        print("Benchmarking runc (default runtime)...")
        runc_results = benchmark_runtime("runc")

        print("\nBenchmarking runsc (gVisor)...")
        runsc_results = benchmark_runtime("gvisor")

        print("\n=== Results ===")
        print("\nrunc (default):")
        for metric, value in runc_results.items():
            print(f"  {metric}: {value:.3f}s")

        print("\nrunsc (gVisor):")
        for metric, value in runsc_results.items():
            print(f"  {metric}: {value:.3f}s")

        print("\nOverhead:")
        for metric in runc_results:
            overhead = ((runsc_results[metric] - runc_results[metric]) / runc_results[metric]) * 100
            print(f"  {metric}: +{overhead:.1f}%")
    ```
  - Files to create: `scripts/benchmark_gvisor.py`

- [ ] **Document gVisor Limitations** (2 hours)
  - Incompatible syscalls and features
  - Performance characteristics
  - Troubleshooting guide
  - Files to create: `docs/security/gvisor-limitations.md`

#### Seccomp Profiles (8 hours)

- [ ] **Create Seccomp Profile for Executor Arm** (4 hours)
  - Audit required syscalls
  - Create allowlist profile
  - Test with realistic workloads
  - Code example:
    ```json
    {
      "defaultAction": "SCMP_ACT_ERRNO",
      "architectures": [
        "SCMP_ARCH_X86_64",
        "SCMP_ARCH_X86",
        "SCMP_ARCH_X32"
      ],
      "syscalls": [
        {
          "names": [
            "accept",
            "accept4",
            "access",
            "arch_prctl",
            "bind",
            "brk",
            "capget",
            "capset",
            "chdir",
            "clone",
            "close",
            "connect",
            "dup",
            "dup2",
            "dup3",
            "epoll_create",
            "epoll_create1",
            "epoll_ctl",
            "epoll_pwait",
            "epoll_wait",
            "execve",
            "exit",
            "exit_group",
            "fchdir",
            "fchown",
            "fcntl",
            "fstat",
            "fstatfs",
            "futex",
            "getcwd",
            "getdents",
            "getdents64",
            "getegid",
            "geteuid",
            "getgid",
            "getpid",
            "getppid",
            "getrlimit",
            "getsockname",
            "getsockopt",
            "gettid",
            "getuid",
            "ioctl",
            "listen",
            "lseek",
            "madvise",
            "memfd_create",
            "mmap",
            "mprotect",
            "munmap",
            "nanosleep",
            "newfstatat",
            "open",
            "openat",
            "pipe",
            "pipe2",
            "poll",
            "ppoll",
            "prctl",
            "pread64",
            "prlimit64",
            "pwrite64",
            "read",
            "readlink",
            "readv",
            "recvfrom",
            "recvmsg",
            "rt_sigaction",
            "rt_sigprocmask",
            "rt_sigreturn",
            "sched_getaffinity",
            "sched_yield",
            "sendmsg",
            "sendto",
            "set_robust_list",
            "set_tid_address",
            "setgid",
            "setgroups",
            "setsockopt",
            "setuid",
            "shutdown",
            "sigaltstack",
            "socket",
            "socketpair",
            "stat",
            "statfs",
            "tgkill",
            "uname",
            "unlink",
            "wait4",
            "write",
            "writev"
          ],
          "action": "SCMP_ACT_ALLOW"
        }
      ]
    }
    ```
  - Files to create: `k8s/security/seccomp-profiles/executor-arm.json`

- [ ] **Audit Syscall Usage** (2 hours)
  - Use strace to capture syscalls
  - Identify minimum required set
  - Code example:
    ```bash
    # scripts/audit_syscalls.sh
    #!/bin/bash
    set -e

    echo "Auditing syscalls for executor-arm..."

    # Run executor-arm under strace
    POD_NAME=$(kubectl get pods -n octollm -l app=executor-arm -o jsonpath='{.items[0].metadata.name}')

    kubectl exec -n octollm $POD_NAME -- \
      strace -c -f -o /tmp/strace.log \
      /usr/local/bin/executor-arm --dry-run

    # Extract syscall names
    kubectl exec -n octollm $POD_NAME -- \
      cat /tmp/strace.log | \
      awk '{print $6}' | \
      sort | uniq > required_syscalls.txt

    echo "Required syscalls saved to required_syscalls.txt"
    ```
  - Files to create: `scripts/audit_syscalls.sh`

- [ ] **Test Seccomp Profile** (2 hours)
  - Deploy with profile enabled
  - Verify functionality
  - Test syscall blocking
  - Code example:
    ```python
    # tests/test_seccomp.py
    import pytest
    import subprocess

    def test_allowed_syscalls():
        """Test that allowed syscalls work."""
        # Deploy executor-arm with seccomp profile
        subprocess.run([
            "kubectl", "apply", "-f", "k8s/arms/executor-deployment.yaml"
        ], check=True)

        # Wait for pod to be ready
        subprocess.run([
            "kubectl", "wait", "--for=condition=ready",
            "pod", "-l", "app=executor-arm",
            "-n", "octollm", "--timeout=60s"
        ], check=True)

        # Test basic functionality (should succeed)
        result = subprocess.run([
            "kubectl", "exec", "-n", "octollm",
            "deployment/executor-arm", "--",
            "ls", "/tmp"
        ], capture_output=True)

        assert result.returncode == 0

    def test_blocked_syscalls():
        """Test that blocked syscalls are denied."""
        # Attempt to use ptrace (should be blocked)
        result = subprocess.run([
            "kubectl", "exec", "-n", "octollm",
            "deployment/executor-arm", "--",
            "strace", "ls"
        ], capture_output=True)

        # Should fail due to seccomp blocking ptrace
        assert result.returncode != 0
        assert b"Operation not permitted" in result.stderr
    ```
  - Files to create: `tests/test_seccomp.py`

#### Network Policies (4 hours)

- [ ] **Create Default Deny Policy** (1 hour)
  - Block all ingress by default
  - Block all egress by default
  - Code example:
    ```yaml
    # k8s/security/network-policies/default-deny.yaml
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
    ```
  - Files to create: `k8s/security/network-policies/default-deny.yaml`

- [ ] **Create Executor Arm Egress Policy** (2 hours)
  - Allow DNS resolution
  - Allow orchestrator communication
  - Allow allowlisted external hosts
  - Code example:
    ```yaml
    # k8s/security/network-policies/executor-arm-egress.yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: executor-arm-egress
      namespace: octollm
    spec:
      podSelector:
        matchLabels:
          app: executor-arm
      policyTypes:
      - Egress
      egress:
      # Allow DNS resolution
      - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
        ports:
        - protocol: UDP
          port: 53

      # Allow orchestrator communication
      - to:
        - podSelector:
            matchLabels:
              app: orchestrator
        ports:
        - protocol: TCP
          port: 8000

      # Allow Redis
      - to:
        - podSelector:
            matchLabels:
              app: redis
        ports:
        - protocol: TCP
          port: 6379

      # Allow specific external hosts (e.g., package registries)
      - to:
        - namespaceSelector: {}
        ports:
        - protocol: TCP
          port: 443
        # Note: This allows HTTPS to any host. In production, use egress
        # gateways with FQDN filtering for more granular control.
    ```
  - Files to create: `k8s/security/network-policies/executor-arm-egress.yaml`

- [ ] **Test Network Isolation** (1 hour)
  - Verify blocked connections fail
  - Verify allowed connections succeed
  - Code example:
    ```bash
    # scripts/test_network_policy.sh
    #!/bin/bash
    set -e

    echo "Testing network policies..."

    POD_NAME=$(kubectl get pods -n octollm -l app=executor-arm -o jsonpath='{.items[0].metadata.name}')

    # Test 1: DNS should work
    echo "Test 1: DNS resolution (should succeed)"
    kubectl exec -n octollm $POD_NAME -- nslookup google.com
    echo "✓ DNS resolution works"

    # Test 2: Orchestrator communication should work
    echo "Test 2: Orchestrator communication (should succeed)"
    kubectl exec -n octollm $POD_NAME -- \
      curl -f http://orchestrator:8000/health
    echo "✓ Orchestrator communication works"

    # Test 3: Blocked host should fail
    echo "Test 3: Blocked host (should fail)"
    if kubectl exec -n octollm $POD_NAME -- \
      curl -f --max-time 5 http://malicious-host.com; then
      echo "✗ FAIL: Blocked host was accessible"
      exit 1
    else
      echo "✓ Blocked host correctly denied"
    fi

    echo "All network policy tests passed"
    ```
  - Files to create: `scripts/test_network_policy.sh`

#### Resource Limits (2 hours)

- [ ] **Configure Resource Quotas** (1 hour)
  - Set namespace-level quotas
  - Prevent resource exhaustion attacks
  - Code example:
    ```yaml
    # k8s/security/resource-quota.yaml
    apiVersion: v1
    kind: ResourceQuota
    metadata:
      name: octollm-quota
      namespace: octollm
    spec:
      hard:
        requests.cpu: "100"
        requests.memory: 200Gi
        limits.cpu: "200"
        limits.memory: 400Gi
        persistentvolumeclaims: "50"
        pods: "200"
    ---
    apiVersion: v1
    kind: LimitRange
    metadata:
      name: octollm-limits
      namespace: octollm
    spec:
      limits:
      - max:
          cpu: "4"
          memory: 8Gi
        min:
          cpu: "100m"
          memory: 128Mi
        default:
          cpu: "1"
          memory: 2Gi
        defaultRequest:
          cpu: "500m"
          memory: 1Gi
        type: Container
      - max:
          cpu: "8"
          memory: 16Gi
        min:
          cpu: "200m"
          memory: 256Mi
        type: Pod
    ```
  - Files to create: `k8s/security/resource-quota.yaml`

- [ ] **Test Resource Limit Enforcement** (1 hour)
  - Test OOM kill behavior
  - Test CPU throttling
  - Verify graceful degradation
  - Files to create: `tests/test_resource_limits.py`

### Testing Requirements

#### Unit Tests
- [ ] Seccomp profile validation (10 test cases)
- [ ] Network policy syntax (5 test cases)
- [ ] Resource limit calculations (5 test cases)

#### Integration Tests
- [ ] gVisor runtime execution
- [ ] Syscall blocking enforcement
- [ ] Network policy enforcement
- [ ] Resource limit enforcement
- [ ] Container escape attempts (should all fail)

#### Security Tests
- [ ] Kernel exploit attempts (CVE-based tests)
- [ ] Container breakout scenarios
- [ ] Resource exhaustion attacks
- [ ] Network scanning from containers

### Documentation Deliverables

- [ ] gVisor deployment guide
- [ ] Seccomp profile maintenance runbook
- [ ] Network policy design patterns
- [ ] Resource sizing guidelines
- [ ] Container escape test report

### Success Criteria

- [ ] All executor containers run under gVisor
- [ ] Seccomp profiles block >99% of unnecessary syscalls
- [ ] Network policies enforce zero-trust model
- [ ] Resource limits prevent DoS attacks
- [ ] Zero successful container escapes in testing

### Common Pitfalls

1. **gVisor Compatibility**: Some syscalls are not supported—audit carefully before deployment
2. **Performance Overhead**: gVisor adds 10-30% latency—budget accordingly in SLAs
3. **Debugging Difficulty**: strace doesn't work with seccomp—use audit logs instead
4. **Network Policy Gaps**: DNS caching can mask policy violations—test with cache cleared
5. **OOM Kill Loops**: Set memory requests = limits to avoid unexpected evictions

### Estimated Effort

- Development: 24 hours
- Testing: 6 hours
- Documentation: 3 hours
- **Total**: 33 hours (~2 weeks for 2 engineers)

### Dependencies

- **Prerequisites**: Sprint 5.1 (capability system for token validation)
- **Blocking**: None
- **Blocked By**: None (can run in parallel with Sprint 5.3)

---

## Sprint 5.3: PII Protection [Week 27-28]

**Duration**: 2 weeks
**Team**: 2 engineers (1 ML, 1 Python)
**Prerequisites**: Phase 2 complete (Safety Guardian Arm deployed)
**Priority**: HIGH

### Sprint Goals

- Implement multi-layer PII detection (regex + NER + LLM)
- Create redaction strategies (masking, tokenization, suppression)
- Add differential privacy for aggregated data
- Achieve >99% PII detection accuracy (F1 score)
- Ensure GDPR/CCPA compliance
- Document PII handling procedures

### Architecture Decisions

**Detection Layers**:
1. **Regex Layer**: Fast pattern matching for common formats (SSN, credit cards, emails)
2. **NER Layer**: Presidio with spaCy models for contextual detection (names, locations)
3. **LLM Layer**: GPT-4 for ambiguous cases and false positive reduction

**Redaction Strategy**: Context-dependent (complete suppression for SSNs, partial masking for emails)
**Storage**: Never store raw PII—always redact before persisting
**Compliance**: GDPR right to erasure, CCPA opt-out, audit trail for all PII access

### Tasks

#### Multi-Layer Detection (12 hours)

- [ ] **Enhance Regex Patterns** (3 hours)
  - Add patterns for all major PII types
  - Implement confidence scoring
  - Reduce false positives
  - Code example:
    ```python
    # arms/safety_guardian/pii/regex_detector.py
    import re
    from typing import List, Dict, Any, Tuple
    from dataclasses import dataclass

    @dataclass
    class PIIMatch:
        """A detected PII instance."""
        pii_type: str
        value: str
        start: int
        end: int
        confidence: float

    class RegexPIIDetector:
        """Fast regex-based PII detection."""

        # Comprehensive regex patterns with confidence scores
        PATTERNS = {
            "ssn": (
                r"\b\d{3}-\d{2}-\d{4}\b",  # 123-45-6789
                0.95
            ),
            "ssn_no_dashes": (
                r"\b\d{9}\b",  # 123456789 (lower confidence, many false positives)
                0.50
            ),
            "credit_card": (
                r"\b(?:\d{4}[-\s]?){3}\d{4}\b",  # 1234-5678-9012-3456
                0.90
            ),
            "email": (
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                0.85
            ),
            "phone_us": (
                r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
                0.80
            ),
            "ip_address": (
                r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
                0.70  # Many false positives (version numbers, etc.)
            ),
            "passport_us": (
                r"\b[0-9]{9}\b",  # US passport number
                0.60  # Low confidence without context
            ),
            "drivers_license": (
                r"\b[A-Z]{1,2}\d{5,7}\b",  # State-dependent format
                0.65
            ),
            "bank_account": (
                r"\b\d{8,17}\b",  # Generic account number
                0.50  # Very low confidence without context
            ),
            "date_of_birth": (
                r"\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b",
                0.75
            ),
            "address": (
                r"\b\d{1,5}\s\w+\s(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir)\b",
                0.70
            ),
        }

        def __init__(self, confidence_threshold: float = 0.70):
            """Initialize detector with confidence threshold."""
            self.confidence_threshold = confidence_threshold
            self.compiled_patterns = {
                pii_type: (re.compile(pattern, re.IGNORECASE), confidence)
                for pii_type, (pattern, confidence) in self.PATTERNS.items()
            }

        def detect(self, text: str) -> List[PIIMatch]:
            """Detect PII in text using regex patterns."""
            matches = []

            for pii_type, (pattern, base_confidence) in self.compiled_patterns.items():
                for match in pattern.finditer(text):
                    value = match.group()

                    # Apply heuristics to adjust confidence
                    confidence = self._adjust_confidence(
                        pii_type, value, base_confidence, text, match.start()
                    )

                    if confidence >= self.confidence_threshold:
                        matches.append(PIIMatch(
                            pii_type=pii_type,
                            value=value,
                            start=match.start(),
                            end=match.end(),
                            confidence=confidence
                        ))

            # Remove overlapping matches (keep highest confidence)
            matches = self._remove_overlaps(matches)

            return matches

        def _adjust_confidence(
            self,
            pii_type: str,
            value: str,
            base_confidence: float,
            text: str,
            position: int
        ) -> float:
            """Adjust confidence based on context and validation."""
            confidence = base_confidence

            # Validation checks
            if pii_type == "credit_card":
                if not self._luhn_check(value.replace("-", "").replace(" ", "")):
                    confidence *= 0.5  # Failed Luhn check

            elif pii_type == "ssn":
                # SSNs can't start with 000, 666, or 900-999
                ssn_digits = value.replace("-", "")
                area = int(ssn_digits[:3])
                if area == 0 or area == 666 or area >= 900:
                    confidence *= 0.3

            elif pii_type == "email":
                # Check for common non-PII email patterns
                if any(domain in value.lower() for domain in ["example.com", "test.com", "localhost"]):
                    confidence *= 0.5

            # Context checks
            context_window = 50
            context_start = max(0, position - context_window)
            context_end = min(len(text), position + len(value) + context_window)
            context = text[context_start:context_end].lower()

            # Boost confidence if PII-related keywords are nearby
            pii_keywords = ["ssn", "social security", "credit card", "phone", "email", "address"]
            if any(keyword in context for keyword in pii_keywords):
                confidence *= 1.1  # Boost by 10%

            # Reduce confidence if in code or structured data
            code_indicators = ["```", "def ", "class ", "function", "var ", "const ", "{", "}"]
            if any(indicator in context for indicator in code_indicators):
                confidence *= 0.7  # Reduce by 30%

            return min(confidence, 1.0)

        def _luhn_check(self, card_number: str) -> bool:
            """Validate credit card using Luhn algorithm."""
            def digits_of(n):
                return [int(d) for d in str(n)]

            digits = digits_of(card_number)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10 == 0

        def _remove_overlaps(self, matches: List[PIIMatch]) -> List[PIIMatch]:
            """Remove overlapping matches, keeping highest confidence."""
            if not matches:
                return []

            # Sort by start position
            matches = sorted(matches, key=lambda m: m.start)

            # Remove overlaps
            result = [matches[0]]
            for match in matches[1:]:
                prev = result[-1]
                if match.start < prev.end:
                    # Overlapping - keep higher confidence
                    if match.confidence > prev.confidence:
                        result[-1] = match
                else:
                    result.append(match)

            return result
    ```
  - Files to update: `arms/safety_guardian/pii/regex_detector.py`

- [ ] **Integrate Presidio NER** (4 hours)
  - Install Presidio framework
  - Configure spaCy models
  - Create custom recognizers
  - Code example:
    ```python
    # arms/safety_guardian/pii/ner_detector.py
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, Pattern, PatternRecognizer
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from typing import List, Dict, Any
    import spacy

    class NERPIIDetector:
        """NER-based PII detection using Presidio."""

        def __init__(self, model_name: str = "en_core_web_lg"):
            """Initialize Presidio with spaCy model."""

            # Configure NLP engine
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": model_name}],
            }
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()

            # Create custom recognizers
            registry = RecognizerRegistry()
            registry.load_predefined_recognizers(nlp_engine=nlp_engine)

            # Add custom recognizers
            self._add_custom_recognizers(registry)

            # Create analyzer
            self.analyzer = AnalyzerEngine(
                nlp_engine=nlp_engine,
                registry=registry
            )

        def _add_custom_recognizers(self, registry: RecognizerRegistry):
            """Add custom PII recognizers."""

            # Medical record numbers
            mrn_recognizer = PatternRecognizer(
                supported_entity="MEDICAL_RECORD_NUMBER",
                patterns=[
                    Pattern(
                        name="mrn_pattern",
                        regex=r"\bMRN[-:\s]?\d{6,10}\b",
                        score=0.85
                    )
                ]
            )
            registry.add_recognizer(mrn_recognizer)

            # Employee IDs
            employee_id_recognizer = PatternRecognizer(
                supported_entity="EMPLOYEE_ID",
                patterns=[
                    Pattern(
                        name="employee_id_pattern",
                        regex=r"\bEMP[-:\s]?\d{5,8}\b",
                        score=0.80
                    )
                ]
            )
            registry.add_recognizer(employee_id_recognizer)

        def detect(self, text: str, language: str = "en") -> List[PIIMatch]:
            """Detect PII using NER."""

            results = self.analyzer.analyze(
                text=text,
                language=language,
                entities=None,  # All entity types
                score_threshold=0.70
            )

            # Convert to PIIMatch format
            matches = []
            for result in results:
                matches.append(PIIMatch(
                    pii_type=result.entity_type.lower(),
                    value=text[result.start:result.end],
                    start=result.start,
                    end=result.end,
                    confidence=result.score
                ))

            return matches
    ```
  - Files to create: `arms/safety_guardian/pii/ner_detector.py`

- [ ] **Implement LLM-Based Detection** (3 hours)
  - Use GPT-4 for ambiguous cases
  - Few-shot prompting for PII identification
  - Code example:
    ```python
    # arms/safety_guardian/pii/llm_detector.py
    from openai import AsyncOpenAI
    from typing import List, Dict, Any
    import json

    class LLMPIIDetector:
        """LLM-based PII detection for ambiguous cases."""

        def __init__(self, openai_client: AsyncOpenAI):
            self.client = openai_client

        async def detect(self, text: str, uncertain_spans: List[Tuple[int, int]]) -> List[PIIMatch]:
            """Use LLM to classify uncertain text spans as PII or not."""

            if not uncertain_spans:
                return []

            # Build prompt with few-shot examples
            prompt = self._build_prompt(text, uncertain_spans)

            # Call LLM
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a PII detection expert. Identify personally identifiable information in the given text spans."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            # Parse response
            result = json.loads(response.choices[0].message.content)

            matches = []
            for item in result.get("detections", []):
                matches.append(PIIMatch(
                    pii_type=item["type"],
                    value=item["value"],
                    start=item["start"],
                    end=item["end"],
                    confidence=item["confidence"]
                ))

            return matches

        def _build_prompt(self, text: str, spans: List[Tuple[int, int]]) -> str:
            """Build few-shot prompt for PII detection."""

            prompt = """Analyze the following text spans and determine if they contain PII (Personally Identifiable Information).

For each span, return:
- type: The type of PII (e.g., "name", "ssn", "email", "phone", "address", "none")
- value: The detected PII value
- start: Start position in text
- end: End position in text
- confidence: Detection confidence (0.0-1.0)

Examples:

Text: "Contact John Smith at john@example.com"
Spans: [(8, 18), (22, 39)]
Output: {
  "detections": [
    {"type": "name", "value": "John Smith", "start": 8, "end": 18, "confidence": 0.95},
    {"type": "email", "value": "john@example.com", "start": 22, "end": 39, "confidence": 0.90}
  ]
}

Text: "The patient's glucose level was 120 mg/dL"
Spans: [(34, 37)]
Output: {
  "detections": [
    {"type": "none", "value": "120", "start": 34, "end": 37, "confidence": 0.85}
  ]
}

Now analyze:

Text: """
            prompt += f"\"{text}\"\n\nSpans: {spans}\n\nOutput:"

            return prompt
    ```
  - Files to create: `arms/safety_guardian/pii/llm_detector.py`

- [ ] **Create Unified Detection Pipeline** (2 hours)
  - Combine all detection layers
  - Aggregate results with confidence voting
  - Code example:
    ```python
    # arms/safety_guardian/pii/unified_detector.py
    from typing import List, Dict, Any
    from collections import defaultdict

    class UnifiedPIIDetector:
        """Multi-layer PII detection with confidence aggregation."""

        def __init__(
            self,
            regex_detector: RegexPIIDetector,
            ner_detector: NERPIIDetector,
            llm_detector: LLMPIIDetector
        ):
            self.regex = regex_detector
            self.ner = ner_detector
            self.llm = llm_detector

        async def detect(self, text: str) -> List[PIIMatch]:
            """Detect PII using all layers and aggregate results."""

            # Layer 1: Regex detection (fast)
            regex_matches = self.regex.detect(text)

            # Layer 2: NER detection (medium speed)
            ner_matches = self.ner.detect(text)

            # Combine regex and NER results
            all_matches = regex_matches + ner_matches

            # Identify uncertain spans (low confidence or conflicting)
            uncertain_spans = self._find_uncertain_spans(all_matches)

            # Layer 3: LLM detection for uncertain spans (slow)
            if uncertain_spans:
                llm_matches = await self.llm.detect(text, uncertain_spans)
                all_matches.extend(llm_matches)

            # Aggregate overlapping detections
            final_matches = self._aggregate_matches(all_matches)

            return final_matches

        def _find_uncertain_spans(
            self,
            matches: List[PIIMatch],
            uncertainty_threshold: float = 0.80
        ) -> List[Tuple[int, int]]:
            """Identify spans with low confidence or conflicts."""

            uncertain = []

            # Group matches by position
            position_groups = defaultdict(list)
            for match in matches:
                position_groups[(match.start, match.end)].append(match)

            for (start, end), group in position_groups.items():
                # Check for low confidence
                max_confidence = max(m.confidence for m in group)
                if max_confidence < uncertainty_threshold:
                    uncertain.append((start, end))
                    continue

                # Check for conflicting types
                types = set(m.pii_type for m in group)
                if len(types) > 1:
                    uncertain.append((start, end))

            return uncertain

        def _aggregate_matches(self, matches: List[PIIMatch]) -> List[PIIMatch]:
            """Aggregate overlapping matches using confidence voting."""

            if not matches:
                return []

            # Group overlapping matches
            groups = []
            sorted_matches = sorted(matches, key=lambda m: m.start)

            current_group = [sorted_matches[0]]
            for match in sorted_matches[1:]:
                # Check if overlaps with current group
                if any(self._overlaps(match, m) for m in current_group):
                    current_group.append(match)
                else:
                    groups.append(current_group)
                    current_group = [match]
            groups.append(current_group)

            # For each group, select best match
            final_matches = []
            for group in groups:
                # Weighted voting by confidence
                type_scores = defaultdict(float)
                for match in group:
                    type_scores[match.pii_type] += match.confidence

                best_type = max(type_scores, key=type_scores.get)
                best_match = max(
                    (m for m in group if m.pii_type == best_type),
                    key=lambda m: m.confidence
                )

                final_matches.append(best_match)

            return final_matches

        def _overlaps(self, match1: PIIMatch, match2: PIIMatch) -> bool:
            """Check if two matches overlap."""
            return not (match1.end <= match2.start or match2.end <= match1.start)
    ```
  - Files to create: `arms/safety_guardian/pii/unified_detector.py`

#### Redaction Strategies (8 hours)

- [ ] **Implement Context-Aware Redaction** (4 hours)
  - Different strategies per PII type
  - Preserve data utility where possible
  - Code example:
    ```python
    # arms/safety_guardian/pii/redactor.py
    from typing import List, Dict, Any, Callable
    import hashlib
    import secrets

    class PIIRedactor:
        """Context-aware PII redaction."""

        def __init__(self, salt: str = None):
            """Initialize redactor with salt for tokenization."""
            self.salt = salt or secrets.token_hex(16)

            # Define redaction strategies per PII type
            self.strategies: Dict[str, Callable] = {
                "ssn": self._redact_complete,
                "credit_card": self._redact_complete,
                "bank_account": self._redact_complete,
                "passport_us": self._redact_complete,
                "email": self._redact_partial_email,
                "phone_us": self._redact_partial_phone,
                "name": self._redact_tokenize,
                "address": self._redact_partial_address,
                "date_of_birth": self._redact_partial_date,
                "ip_address": self._redact_partial_ip,
            }

        def redact(self, text: str, matches: List[PIIMatch]) -> str:
            """Redact PII from text using context-aware strategies."""

            # Sort matches by position (reverse order to preserve positions)
            sorted_matches = sorted(matches, key=lambda m: m.start, reverse=True)

            redacted_text = text
            for match in sorted_matches:
                strategy = self.strategies.get(
                    match.pii_type,
                    self._redact_complete  # Default to complete redaction
                )

                replacement = strategy(match)
                redacted_text = (
                    redacted_text[:match.start] +
                    replacement +
                    redacted_text[match.end:]
                )

            return redacted_text

        def _redact_complete(self, match: PIIMatch) -> str:
            """Completely redact PII (replace with placeholder)."""
            return f"[REDACTED_{match.pii_type.upper()}]"

        def _redact_partial_email(self, match: PIIMatch) -> str:
            """Partially redact email (keep domain)."""
            email = match.value
            if "@" in email:
                local, domain = email.split("@", 1)
                # Keep first character of local part
                redacted_local = local[0] + "***" if local else "***"
                return f"{redacted_local}@{domain}"
            return "[REDACTED_EMAIL]"

        def _redact_partial_phone(self, match: PIIMatch) -> str:
            """Partially redact phone number (keep last 4 digits)."""
            import re
            digits = re.sub(r'\D', '', match.value)
            if len(digits) >= 10:
                return f"***-***-{digits[-4:]}"
            return "[REDACTED_PHONE]"

        def _redact_partial_address(self, match: PIIMatch) -> str:
            """Partially redact address (keep city/state if present)."""
            # Simplistic: Just redact street number
            import re
            return re.sub(r'\d+', '***', match.value)

        def _redact_partial_date(self, match: PIIMatch) -> str:
            """Partially redact date of birth (keep year)."""
            import re
            # Attempt to extract year
            year_match = re.search(r'(19|20)\d{2}', match.value)
            if year_match:
                year = year_match.group()
                return f"**/**/{ year}"
            return "[REDACTED_DOB]"

        def _redact_partial_ip(self, match: PIIMatch) -> str:
            """Partially redact IP address (keep first two octets)."""
            parts = match.value.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.*.*"
            return "[REDACTED_IP]"

        def _redact_tokenize(self, match: PIIMatch) -> str:
            """Tokenize PII (consistent hash for same value)."""
            # Create deterministic hash
            token_input = f"{match.value}{self.salt}"
            hash_value = hashlib.sha256(token_input.encode()).hexdigest()[:12]
            return f"[TOKEN_{match.pii_type.upper()}_{hash_value}]"
    ```
  - Files to create: `arms/safety_guardian/pii/redactor.py`

- [ ] **Add Differential Privacy** (2 hours)
  - Implement Laplace mechanism for aggregated data
  - Configure privacy budget (epsilon)
  - Code example:
    ```python
    # arms/safety_guardian/privacy/differential_privacy.py
    import numpy as np
    from typing import List, Dict, Any

    class DifferentialPrivacy:
        """Differential privacy for aggregated data."""

        def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
            """Initialize with privacy budget."""
            self.epsilon = epsilon
            self.delta = delta

        def add_laplace_noise(
            self,
            true_value: float,
            sensitivity: float = 1.0
        ) -> float:
            """Add Laplace noise to a numeric value."""
            scale = sensitivity / self.epsilon
            noise = np.random.laplace(0, scale)
            return true_value + noise

        def add_gaussian_noise(
            self,
            true_value: float,
            sensitivity: float = 1.0
        ) -> float:
            """Add Gaussian noise (for (epsilon, delta)-DP)."""
            sigma = np.sqrt(2 * np.log(1.25 / self.delta)) * sensitivity / self.epsilon
            noise = np.random.normal(0, sigma)
            return true_value + noise

        def privatize_histogram(
            self,
            histogram: Dict[str, int],
            sensitivity: float = 1.0
        ) -> Dict[str, int]:
            """Add noise to histogram counts."""
            noisy_histogram = {}
            for key, count in histogram.items():
                noisy_count = self.add_laplace_noise(count, sensitivity)
                # Ensure non-negative
                noisy_histogram[key] = max(0, int(round(noisy_count)))
            return noisy_histogram

        def privatize_average(
            self,
            values: List[float],
            lower_bound: float,
            upper_bound: float
        ) -> float:
            """Compute differentially private average."""
            # Clip values to bounds
            clipped = [max(lower_bound, min(upper_bound, v)) for v in values]

            # Sensitivity is (upper_bound - lower_bound) / n
            sensitivity = (upper_bound - lower_bound) / len(clipped)

            true_avg = sum(clipped) / len(clipped)
            return self.add_laplace_noise(true_avg, sensitivity)
    ```
  - Files to create: `arms/safety_guardian/privacy/differential_privacy.py`

- [ ] **Create Audit Trail for PII Access** (2 hours)
  - Log all PII detection events
  - Track redaction decisions
  - GDPR/CCPA compliance reporting
  - Files to update: `orchestrator/audit/pii_logger.py`

#### Testing and Compliance (4 hours)

- [ ] **Create PII Detection Test Suite** (2 hours)
  - Benchmark dataset with labeled PII
  - Calculate precision, recall, F1 score
  - Target: >99% F1 score
  - Code example:
    ```python
    # tests/test_pii_detection.py
    import pytest
    from typing import List, Tuple

    # Test dataset with labeled PII
    TEST_CASES = [
        (
            "My SSN is 123-45-6789 and email is john@example.com",
            [("ssn", 10, 21), ("email", 36, 53)]
        ),
        (
            "Call me at (555) 123-4567 or 555-987-6543",
            [("phone_us", 11, 25), ("phone_us", 29, 41)]
        ),
        (
            "John Smith lives at 123 Main Street, New York, NY 10001",
            [("name", 0, 10), ("address", 20, 56)]
        ),
        # ... 100+ more test cases
    ]

    @pytest.mark.asyncio
    async def test_pii_detection_accuracy(unified_detector):
        """Test PII detection accuracy on benchmark dataset."""

        true_positives = 0
        false_positives = 0
        false_negatives = 0

        for text, expected_pii in TEST_CASES:
            detected = await unified_detector.detect(text)

            # Convert to set of (type, start, end) tuples
            detected_set = {(m.pii_type, m.start, m.end) for m in detected}
            expected_set = set(expected_pii)

            tp = len(detected_set & expected_set)
            fp = len(detected_set - expected_set)
            fn = len(expected_set - detected_set)

            true_positives += tp
            false_positives += fp
            false_negatives += fn

        # Calculate metrics
        precision = true_positives / (true_positives + false_positives)
        recall = true_positives / (true_positives + false_negatives)
        f1_score = 2 * (precision * recall) / (precision + recall)

        print(f"Precision: {precision:.3f}")
        print(f"Recall: {recall:.3f}")
        print(f"F1 Score: {f1_score:.3f}")

        # Assert F1 score > 99%
        assert f1_score >= 0.99, f"F1 score {f1_score:.3f} below target 0.99"
    ```
  - Files to create: `tests/test_pii_detection.py`

- [ ] **GDPR Compliance Verification** (1 hour)
  - Right to erasure (delete all user data)
  - Data portability (export user data)
  - Consent management
  - Files to create: `docs/compliance/gdpr-procedures.md`

- [ ] **CCPA Compliance Verification** (1 hour)
  - Opt-out mechanisms
  - Data disclosure reporting
  - Files to create: `docs/compliance/ccpa-procedures.md`

### Testing Requirements

#### Unit Tests
- [ ] Regex pattern accuracy (30 test cases per pattern)
- [ ] NER model accuracy (50 test cases)
- [ ] LLM detection accuracy (20 test cases)
- [ ] Redaction strategies (15 test cases)
- [ ] Differential privacy noise distribution (10 test cases)

#### Integration Tests
- [ ] End-to-end detection pipeline
- [ ] Multi-layer aggregation
- [ ] Redaction preservation of data utility
- [ ] Audit log completeness

#### Performance Tests
- [ ] Detection latency (<100ms for regex, <500ms for NER, <2s for LLM)
- [ ] Throughput (>100 requests/second)

### Documentation Deliverables

- [ ] PII detection architecture diagram
- [ ] Supported PII types reference
- [ ] Redaction strategy guide
- [ ] Differential privacy parameter tuning
- [ ] GDPR/CCPA compliance procedures

### Success Criteria

- [ ] F1 score >99% on benchmark dataset
- [ ] Zero PII stored in database (all redacted)
- [ ] Audit trail for 100% of PII access
- [ ] GDPR/CCPA compliance verified
- [ ] Detection latency <2s (P95)

### Common Pitfalls

1. **False Positives**: Version numbers (e.g., "1.2.3.4") detected as IP addresses—use context checks
2. **False Negatives**: International formats (non-US phone numbers, addresses)—expand regex patterns
3. **Performance**: LLM detection is slow—only use for uncertain spans
4. **Context Loss**: Aggressive redaction removes too much context—use partial redaction
5. **Compliance Gaps**: Missing audit logs for read operations—log all PII access, not just writes

### Estimated Effort

- Development: 24 hours
- Testing: 6 hours
- Documentation: 3 hours
- **Total**: 33 hours (~2 weeks for 2 engineers)

### Dependencies

- **Prerequisites**: Safety Guardian Arm deployed (Phase 2)
- **Blocking**: None
- **Blocked By**: None (can run in parallel with other sprints)

---

## Sprint 5.4: Security Testing [Week 29-30]

**(Abbreviated for space - full version would be 1,000-1,200 lines)**

### Sprint Goals

- Set up SAST (Bandit, Semgrep, cargo-audit)
- Set up DAST (ZAP, Burp Suite, custom scanners)
- Implement dependency vulnerability scanning
- Conduct penetration testing
- Automate security testing in CI/CD
- Create security testing runbooks

### Key Tasks (Summary)

1. **SAST Integration** (8 hours)
   - Configure Bandit for Python code scanning
   - Configure Semgrep with custom rules
   - Configure cargo-audit for Rust dependencies
   - Integrate into GitHub Actions CI

2. **DAST Integration** (8 hours)
   - Set up OWASP ZAP for API testing
   - Create custom exploit scripts
   - Test for OWASP Top 10 vulnerabilities
   - Automate in staging environment

3. **Dependency Scanning** (4 hours)
   - Configure Dependabot for automated PRs
   - Set up Snyk for vulnerability monitoring
   - Create dependency update policy

4. **Penetration Testing** (12 hours)
   - Contract external security firm
   - Conduct internal testing (OWASP testing guide)
   - Document findings and remediation
   - Retest after fixes

5. **CI/CD Integration** (4 hours)
   - Add security gates to pipeline
   - Block deploys on critical vulnerabilities
   - Generate security reports

### Estimated Effort: 36 hours (~2 weeks for 2 engineers)

---

## Sprint 5.5: Audit Logging [Week 31-32]

**(Abbreviated for space - full version would be 800-1,000 lines)**

### Sprint Goals

- Implement provenance tracking for all artifacts
- Create immutable audit log storage (WORM)
- Build compliance reporting dashboards
- Ensure 100% coverage of security events
- Document audit log retention policies
- Create forensic analysis procedures

### Key Tasks (Summary)

1. **Provenance Tracking** (8 hours)
   - Track artifact lineage (inputs → processing → outputs)
   - Record all LLM calls with prompts and responses
   - Store task execution graphs
   - Cryptographic signing of artifacts

2. **Immutable Audit Logs** (8 hours)
   - Use PostgreSQL with append-only tables
   - Implement Write-Once-Read-Many (WORM) storage
   - Merkle tree for tamper detection
   - Archive to S3 Glacier for long-term retention

3. **Compliance Reporting** (6 hours)
   - Build Grafana dashboards for SOC 2, ISO 27001
   - Automate report generation
   - GDPR/CCPA data access reports

4. **Security Event Monitoring** (6 hours)
   - Monitor for anomalous access patterns
   - Alert on suspicious activities
   - Integration with SIEM systems

5. **Forensic Procedures** (4 hours)
   - Document incident response runbooks
   - Create audit log analysis tools
   - Train team on forensic investigation

### Estimated Effort: 32 hours (~2 weeks for 2 engineers)

---

## Phase 5 Summary

**Total Tasks**: 60+ security hardening tasks across 5 sprints
**Estimated Duration**: 8-10 weeks with 3-4 engineers
**Total Estimated Hours**: ~160 hours development + ~30 hours testing + ~20 hours documentation = 210 hours

**Deliverables**:
- Capability-based access control system
- Container sandboxing with gVisor
- Multi-layer PII protection (>99% accuracy)
- Comprehensive security testing automation
- Immutable audit logging with compliance reporting

**Completion Checklist**:
- [ ] All API calls require capability tokens
- [ ] All containers run under gVisor with seccomp
- [ ] PII detection F1 score >99%
- [ ] Zero high-severity vulnerabilities in production
- [ ] 100% security event audit coverage
- [ ] GDPR/CCPA compliance verified
- [ ] Penetration test passed

**Next Phase**: Phase 6 (Production Readiness)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-10
**Maintained By**: OctoLLM Security Team
