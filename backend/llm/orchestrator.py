import uuid
from enum import Enum
from typing import Any

from agents import Runner
from loguru import logger

from backend.llm.agents import (
    mapping_evaluation_agent,
    measurement_agent,
    measurement_data_agent,
    protein_agent,
    small_molecule_agent,
)
from backend.llm.models import EvaluationReport

CONTEXT: list[dict[str, Any]] = []


class Phase(str, Enum):
    EVALUATE = "map"
    CLARIFY = "clarify"
    BUILD = "build"
    CHECK = "check"
    DONE = "done"


class AgentOrchestrator:
    def __init__(self):
        self.phase = Phase.EVALUATE
        self.context = CONTEXT
        self.session_id = str(uuid.uuid4())

    async def evaluate(self, user_input: str) -> EvaluationReport:
        phase = Phase.EVALUATE
        # 1) run all agents for this phase
        reports = []
        for agent in [
            small_molecule_agent,
            protein_agent,
            measurement_agent,
            measurement_data_agent,
        ]:
            logger.info(f"Running {agent.name}...")
            result = await Runner.run(
                starting_agent=agent,
                input=user_input,
                context=self.context,
            )
            report = result.final_output
            report.agent_name = agent.name
            logger.info(f"Received report from {agent.name}: {result.final_output}")
            reports.append(result.final_output)

        # 2) evaluate the reports by the mapping_evaluation_agent
        logger.info(f"Evaluating reports by {mapping_evaluation_agent.name}...")
        message = f"""
        Here are the reports from the individual agents:
        {reports}
        """
        evaluation_report = await Runner.run(
            starting_agent=mapping_evaluation_agent,
            input=message,
            context=self.context,
        )

        return evaluation_report.final_output
