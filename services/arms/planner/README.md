# Planner Arm

The Planner Arm specializes in task decomposition, breaking complex goals into actionable subtasks with acceptance criteria.

## Overview

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **LLM**: GPT-3.5-turbo (cost-optimized)
- **Capabilities**: Task decomposition, dependency analysis, constraint verification

## Functionality

Given a high-level goal, the Planner produces:

1. **Subtask List** - Ordered steps to achieve goal
2. **Dependencies** - Task ordering constraints
3. **Acceptance Criteria** - Measurable success conditions
4. **Resource Estimates** - Time, tokens, cost predictions
5. **Risk Assessment** - Potential failure modes

## Input Schema

```python
class PlanRequest(BaseModel):
    task_id: str
    goal: str
    constraints: Dict[str, Any]
    context: Optional[str] = None
    max_subtasks: int = 10
```

## Output Schema

```python
class PlanResponse(BaseModel):
    task_id: str
    subtasks: List[Subtask]
    dependencies: List[Tuple[str, str]]
    estimated_duration: int  # seconds
    estimated_cost: float  # USD
    confidence: float  # 0.0-1.0
```

## Development

```bash
cd services/arms/planner
poetry install
poetry run pytest tests/ -v
poetry run uvicorn src.main:app --reload --port 8001
```

## References

- [Planner Arm Specification](../../../docs/components/arms/planner.md)
- [API Contracts](../../../docs/api/component-contracts.md)
