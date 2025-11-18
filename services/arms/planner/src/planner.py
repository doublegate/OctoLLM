"""
Core planning logic for the Planner Arm.

Implements task decomposition using OpenAI's GPT-3.5-turbo with structured output.
"""

import json
from typing import Any

import structlog
from openai import AsyncOpenAI, OpenAIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import Settings
from src.models import PlanResponse
from src.prompts import SYSTEM_PROMPT, build_user_prompt

logger = structlog.get_logger(__name__)


class PlanningError(Exception):
    """Base exception for planning errors."""

    pass


class InvalidDependencyError(PlanningError):
    """Raised when dependencies are invalid."""

    pass


class PlanningTimeoutError(PlanningError):
    """Raised when planning exceeds timeout."""

    pass


class LLMError(PlanningError):
    """Raised when LLM API fails."""

    pass


class PlannerArm:
    """
    Task decomposition specialist using LLM-based planning.

    Uses OpenAI's GPT-3.5-turbo to break complex goals into actionable subtasks
    with dependencies, acceptance criteria, and resource estimates.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the Planner Arm.

        Args:
            settings: Application settings including OpenAI API key
        """
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.llm_timeout,
        )
        self.model = settings.llm_model
        self.temperature = settings.planning_temperature
        self.max_tokens = settings.max_tokens
        logger.info(
            "planner_arm.initialized",
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    async def generate_plan(
        self, goal: str, constraints: list[str], context: dict[str, Any]
    ) -> PlanResponse:
        """
        Generate execution plan for a given goal.

        Args:
            goal: Natural language description of what to accomplish
            constraints: List of hard constraints (time, cost, safety)
            context: Additional background information

        Returns:
            PlanResponse with ordered subtasks and metadata

        Raises:
            PlanningError: If planning fails
            InvalidDependencyError: If dependencies are invalid
            LLMError: If LLM API fails
        """
        logger.info("planner_arm.generate_plan.start", goal=goal[:100], constraints=constraints)

        try:
            # Build prompt
            user_prompt = build_user_prompt(goal, constraints, context)

            # Call LLM with retry logic
            response_content = await self._call_llm(user_prompt)

            # Parse JSON response
            plan_data = self._parse_llm_response(response_content)

            # Calculate total duration
            total_duration = sum(
                step.get("estimated_duration_seconds", 30) for step in plan_data["plan"]
            )
            plan_data["total_estimated_duration"] = total_duration

            # Validate dependencies
            self._validate_dependencies(plan_data["plan"])

            # Validate plan size
            if len(plan_data["plan"]) < self.settings.min_plan_steps:
                raise PlanningError(
                    f"Plan has only {len(plan_data['plan'])} steps, "
                    f"minimum is {self.settings.min_plan_steps}"
                )
            if len(plan_data["plan"]) > self.settings.max_plan_steps:
                raise PlanningError(
                    f"Plan has {len(plan_data['plan'])} steps, "
                    f"maximum is {self.settings.max_plan_steps}"
                )

            # Create validated response
            plan_response = PlanResponse(**plan_data)

            logger.info(
                "planner_arm.generate_plan.success",
                steps=len(plan_response.plan),
                duration=plan_response.total_estimated_duration,
                confidence=plan_response.confidence,
                complexity=plan_response.complexity_score,
            )

            return plan_response

        except json.JSONDecodeError as e:
            logger.error("planner_arm.generate_plan.json_parse_error", error=str(e))
            raise PlanningError(f"Failed to parse LLM response as JSON: {e}") from e
        except InvalidDependencyError:
            raise
        except Exception as e:
            logger.error("planner_arm.generate_plan.error", error=str(e))
            raise PlanningError(f"Planning failed: {e}") from e

    @retry(
        retry=retry_if_exception_type(OpenAIError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_llm(self, user_prompt: str) -> str:
        """
        Call OpenAI API with retry logic.

        Args:
            user_prompt: User prompt for planning

        Returns:
            LLM response content

        Raises:
            LLMError: If LLM API fails after retries
        """
        try:
            logger.debug("planner_arm.llm_call.start", prompt_length=len(user_prompt))

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},  # Ensure JSON output
            )

            content = response.choices[0].message.content
            if not content:
                raise LLMError("LLM returned empty response")

            logger.debug(
                "planner_arm.llm_call.success",
                response_length=len(content),
                model=response.model,
                tokens_used=response.usage.total_tokens if response.usage else 0,
            )

            return content

        except OpenAIError as e:
            logger.warning("planner_arm.llm_call.retry", error=str(e))
            raise
        except Exception as e:
            logger.error("planner_arm.llm_call.error", error=str(e))
            raise LLMError(f"LLM API call failed: {e}") from e

    def _parse_llm_response(self, content: str) -> dict[str, Any]:
        """
        Parse LLM JSON response.

        Args:
            content: Raw LLM response content

        Returns:
            Parsed plan dictionary

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        try:
            data = json.loads(content)

            # Validate required fields
            if "plan" not in data:
                raise ValueError("Response missing 'plan' field")
            if "rationale" not in data:
                raise ValueError("Response missing 'rationale' field")
            if "confidence" not in data:
                raise ValueError("Response missing 'confidence' field")

            # Add default complexity if missing
            if "complexity_score" not in data:
                data["complexity_score"] = self._calculate_complexity(data["plan"])

            return data

        except json.JSONDecodeError as e:
            logger.error(
                "planner_arm.parse_response.json_error", error=str(e), content=content[:500]
            )
            raise

    def _validate_dependencies(self, steps: list[dict[str, Any]]) -> None:
        """
        Ensure dependencies reference valid steps.

        Args:
            steps: List of step dictionaries

        Raises:
            InvalidDependencyError: If dependencies are invalid
        """
        step_numbers = {step["step"] for step in steps}

        for step in steps:
            step_num = step["step"]
            depends_on = step.get("depends_on", [])

            for dep in depends_on:
                # Check dependency exists
                if dep not in step_numbers:
                    raise InvalidDependencyError(
                        f"Step {step_num} depends on non-existent step {dep}"
                    )

                # Check no forward dependencies
                if dep >= step_num:
                    raise InvalidDependencyError(
                        f"Step {step_num} cannot depend on later or same step {dep}"
                    )

        # Check for circular dependencies (simple check)
        # More sophisticated cycle detection could be added here
        logger.debug("planner_arm.validate_dependencies.success", total_steps=len(steps))

    def _calculate_complexity(self, steps: list[dict[str, Any]]) -> float:
        """
        Calculate plan complexity score.

        Args:
            steps: List of step dictionaries

        Returns:
            Complexity score (0.0-1.0)
        """
        if not steps:
            return 0.0

        # Factors contributing to complexity:
        # - Number of steps (more = more complex)
        # - Number of dependencies (more = more complex)
        # - Cost tiers (higher = more complex)

        num_steps = len(steps)
        total_deps = sum(len(step.get("depends_on", [])) for step in steps)
        avg_cost = sum(step.get("estimated_cost_tier", 2) for step in steps) / num_steps

        # Normalize factors (rough heuristic)
        step_factor = min(num_steps / 10.0, 1.0)  # 10+ steps = max complexity
        dep_factor = min(total_deps / 10.0, 1.0)  # 10+ deps = max complexity
        cost_factor = (avg_cost - 1) / 4.0  # Normalize cost tier to 0-1

        # Weighted average
        complexity = (0.4 * step_factor) + (0.3 * dep_factor) + (0.3 * cost_factor)

        return min(max(complexity, 0.0), 1.0)  # Clamp to [0, 1]
