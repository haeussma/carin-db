import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from agents import Runner
from loguru import logger

from backend.llm.agents import (
    measurement_agent,
    measurement_data_agent,
    protein_agent,
    small_molecule_agent,
)


class Phase(str, Enum):
    EVALUATE = "map"
    CLARIFY = "clarify"
    BUILD = "build"
    CHECK = "check"
    DONE = "done"


class ConversationPhase(str, Enum):
    DISCOVERY = "discovery"  # Running initial mapping agents
    REVIEW = "review"  # User reviewing mapping reports
    CLARIFICATION = "clarification"  # User clarifying specific mappings
    SPECIES_ANALYSIS = "species_analysis"  # Running species distinguisher
    SPECIES_REVIEW = "species_review"  # User reviewing species findings
    FINALIZATION = "finalization"  # Generating final document


class MappingStatus(str, Enum):
    PENDING = "pending"  # Just discovered, awaiting user input
    APPROVED = "approved"  # User approved this mapping
    REJECTED = "rejected"  # User rejected this mapping
    CLARIFYING = "clarifying"  # User requested clarification
    RESOLVED = "resolved"  # Clarification completed


@dataclass
class MappingEntry:
    """Represents a single attribute mapping with user interaction state"""

    agent_name: str  # e.g., "small_molecule_agent"
    object_type: str  # e.g., "SmallMolecule"
    attribute: str  # e.g., "name"
    graph_location: Optional[str]  # e.g., "Molecule.NAME"
    confidence: float = 0.0
    status: MappingStatus = MappingStatus.PENDING
    user_feedback: Optional[str] = None
    ambiguous_options: list[str] = field(default_factory=list)
    is_required: bool = False


class ChatState:
    """Extended version of your existing ChatState"""

    def __init__(self, history: list[dict[str, str]] = [], max_turns: int = 20):
        # Keep your existing fields
        self.turn_count = 0
        self.max_turns = max_turns
        self.history = history

        # Add new interactive fields
        self.current_phase: ConversationPhase = ConversationPhase.DISCOVERY
        self.mapping_entries: Dict[
            str, MappingEntry
        ] = {}  # key: f"{agent}_{attribute}"
        self.agent_reports: Dict[str, Any] = {}  # Store original MappingReport objects
        self.species_analysis: Optional[Any] = None
        self.current_mapping_under_review: Optional[str] = None  # mapping_entry key
        self.final_document: Optional[dict] = None

    # Keep your existing methods
    def add_user_history(self, content: str): ...
    def add_system_history(self, content: str): ...
    def get_history_string(self, n_messages: None | int = None): ...

    # Add new methods
    def add_mapping_entry(self, entry: MappingEntry) -> str:
        """Add a mapping entry and return its key"""
        key = f"{entry.agent_name}_{entry.attribute}"
        self.mapping_entries[key] = entry
        return key

    def get_next_pending_mapping(self) -> Optional[MappingEntry]:
        """Get the next mapping that needs user review"""
        for entry in self.mapping_entries.values():
            if entry.status == MappingStatus.PENDING:
                return entry
        return None

    def get_approved_mappings_by_type(self, object_type: str) -> Dict[str, str]:
        """Get approved mappings for a specific object type"""
        return {
            entry.attribute: entry.graph_location
            for entry in self.mapping_entries.values()
            if entry.object_type == object_type
            and entry.status == MappingStatus.APPROVED
        }

    def advance_phase(self):
        """Move to next conversation phase"""
        phase_order = [
            ConversationPhase.DISCOVERY,
            ConversationPhase.REVIEW,
            ConversationPhase.SPECIES_ANALYSIS,
            ConversationPhase.SPECIES_REVIEW,
            ConversationPhase.FINALIZATION,
        ]
        current_idx = phase_order.index(self.current_phase)
        if current_idx < len(phase_order) - 1:
            self.current_phase = phase_order[current_idx + 1]

    def is_discovery_complete(self) -> bool:
        """Check if all required mappings have been addressed"""
        required_pending = [
            entry
            for entry in self.mapping_entries.values()
            if entry.is_required and entry.status == MappingStatus.PENDING
        ]
        return len(required_pending) == 0


class AgentOrchestrator:
    def __init__(self):
        self.phase = Phase.EVALUATE
        self.context = []
        self.session_id = str(uuid.uuid4())

    async def evaluate(self, user_input: str, chat_state: ChatState) -> dict:
        """Route based on conversation phase"""
        if chat_state.current_phase == ConversationPhase.DISCOVERY:
            return await self.run_discovery_phase(user_input, chat_state)
        elif chat_state.current_phase == ConversationPhase.REVIEW:
            return await self.handle_mapping_review(user_input, chat_state)
        elif chat_state.current_phase == ConversationPhase.CLARIFICATION:
            return await self.handle_clarification(user_input, chat_state)
        elif chat_state.current_phase == ConversationPhase.SPECIES_ANALYSIS:
            return await self.run_species_analysis(chat_state)
        # ... etc

    async def run_discovery_phase(self, user_input: str, chat_state: ChatState) -> dict:
        """Your existing logic + populate mapping entries"""
        # Run your existing agent pipeline
        reports = []
        tasks = [
            Runner.run(
                starting_agent=agent,
                input=user_input,
                context=self.context,
            )
            for agent in [
                small_molecule_agent,
                protein_agent,
                measurement_agent,
                measurement_data_agent,
            ]
        ]
        logger.info(f"Running {len(tasks)} tasks")
        results = await asyncio.gather(*tasks)
        logger.info(f"Received {len(results)} results")

        for agent, result in zip(
            [
                small_molecule_agent,
                protein_agent,
                measurement_agent,
                measurement_data_agent,
            ],
            results,
        ):
            report = result.final_output
            report.agent_name = agent.name
            logger.info(f"Received report from {agent.name}: {result.final_output}")
            reports.append(report)

        # Store reports and convert to mapping entries
        for agent, result in zip(
            [
                "small_molecule_agent",
                "protein_agent",
                "measurement_agent",
                "measurement_data_agent",
            ],
            results,
        ):
            chat_state.agent_reports[agent] = result.final_output
            self.populate_mapping_entries(agent, result.final_output, chat_state)

        # Move to review phase
        chat_state.current_phase = ConversationPhase.REVIEW

        return await self.present_first_mapping_for_review(chat_state)

    def populate_mapping_entries(
        self, agent_name: str, mapping_report: Any, chat_state: ChatState
    ):
        """Convert MappingReport to MappingEntry objects"""
        # Extract from your MappingReport structure
        # This depends on your exact MappingReport format
        for found_mapping in mapping_report.found_mappings:
            entry = MappingEntry(
                agent_name=agent_name,
                object_type=found_mapping.object_type,  # You'll need to adapt to your actual structure
                attribute=found_mapping.attribute,
                graph_location=found_mapping.graph_location,
                confidence=found_mapping.confidence,
                status=MappingStatus.PENDING,
                is_required=found_mapping.is_required,
            )
            chat_state.add_mapping_entry(entry)

        # Handle ambiguous mappings
        for ambiguous_mapping in mapping_report.ambiguous_mappings:
            entry = MappingEntry(
                agent_name=agent_name,
                object_type=ambiguous_mapping.object_type,
                attribute=ambiguous_mapping.attribute,
                graph_location=None,  # No single choice yet
                confidence=0.5,
                status=MappingStatus.PENDING,
                ambiguous_options=ambiguous_mapping.options,
                is_required=ambiguous_mapping.is_required,
            )
            chat_state.add_mapping_entry(entry)

    async def handle_mapping_review(
        self, user_input: str, chat_state: ChatState
    ) -> dict:
        # Implementation of handle_mapping_review method
        pass

    async def handle_clarification(
        self, user_input: str, chat_state: ChatState
    ) -> dict:
        # Implementation of handle_clarification method
        pass

    async def run_species_analysis(self, chat_state: ChatState) -> dict:
        # Implementation of run_species_analysis method
        pass

    async def present_first_mapping_for_review(self, chat_state: ChatState) -> dict:
        # Implementation of present_first_mapping_for_review method
        pass
