# Glossary

## A

**Active Inference** - Design principle where the system proactively reduces uncertainty rather than waiting for instructions.

**Arm** - Specialized module in the OctoLLM architecture responsible for domain-specific tasks (Planner, Tool Executor, Retriever, Coder, Judge, Safety Guardian).

**ArmCapability** - Data structure describing an arm's interface, capabilities, and resource requirements.

## C

**Circuit Breaker** - Resilience pattern preventing cascading failures when external services are unavailable.

**Coder Arm** - Specialized module for code generation, debugging, and refactoring.

## D

**Distributed Autonomy** - Design principle where arms make local decisions while the orchestrator provides global coordination.

**Distributed Memory** - Hybrid memory architecture with global semantic memory and local episodic stores per arm.

## E

**Episodic Memory** - Short-term, task-specific memory stored locally in each arm (Redis-backed).

## G

**Global Semantic Memory** - Project-wide knowledge graph stored in PostgreSQL with vector embeddings for search.

## H

**Hierarchical Processing** - Design principle reserving expensive LLM resources for complex problems by using reflex layer and small models first.

## J

**Judge Arm** - Specialized module for output validation and quality assurance.

## M

**Mixture of Experts (MoE)** - Architecture pattern using multiple specialized models with a gating mechanism.

**Modular Specialization** - Design principle where each component excels at one thing and delegates everything else.

## O

**Orchestrator** - Central "brain" service coordinating task decomposition and arm delegation using frontier LLMs.

## P

**Planner Arm** - Specialized module for task decomposition and workflow generation.

**Provenance Metadata** - Tracking information for every artifact (arm, timestamp, command hash, data sources, tests).

## R

**Reflex Layer** - Fast preprocessing layer for pattern matching and caching without LLM involvement.

**Retriever Arm** - Specialized module for knowledge base search and information retrieval.

## S

**Safety Guardian Arm** - Specialized module for PII detection, content filtering, and safety checks.

**Semantic Memory** - See Global Semantic Memory.

**Swarm Decision-Making** - Pattern where N parallel proposals are aggregated with conflict resolution.

## T

**TaskContract** - Core data structure representing a task with goal, constraints, budget, and acceptance criteria.

**Tool Executor Arm** - Specialized module for executing external commands in sandboxed environments.

## See Also

- [Architecture Overview](../architecture/overview.md)
- [Data Structures](../architecture/data-structures.md)
- [Component Documentation](../components/reflex-layer.md)
