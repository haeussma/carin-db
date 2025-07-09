import asyncio
import json
from enum import Enum
from typing import Optional

from agents import Agent, Runner
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel

from ...llm.agents import (
    mapping_file_checker_agent,
    measurement_agent,
    protein_agent,
    small_molecule_agent,
    species_distinguisher_agent,
)
from ...llm.models import EnzymeMLMappings, MappingReport, SpeciesTraversalReport

router = APIRouter(prefix="/chat")

AGENTS: dict[str, Agent] = {
    small_molecule_agent.name: small_molecule_agent,
    protein_agent.name: protein_agent,
    measurement_agent.name: measurement_agent,
}


class ConversationPhase(str, Enum):
    DISCOVERY = "discovery"  # Running all agents in parallel
    AGENT_REVIEW = "agent_review"  # User reviewing agent results one by one
    SPECIES_ANALYSIS = "species_analysis"  # Running species analysis
    SPECIES_TRAVERSAL_REVIEW = (
        "species_traversal_review"  # User reviewing individual species traversals
    )
    FINALIZATION = "finalization"
    EXISTING_MAPPING_CHOICE = "existing_mapping_choice"


class MappingStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MappingEntry(BaseModel):
    object_name: str
    status: MappingStatus = MappingStatus.PENDING
    report: MappingReport
    user_feedback: str | None = None  # Store user feedback

    class Config:
        arbitrary_types_allowed = True


class ChatState:
    """Interactive chat state: run all agents, then review one by one"""

    def __init__(
        self,
        turn_count: int = 0,
        history: list[dict] = [],
        phase: ConversationPhase = ConversationPhase.DISCOVERY,
        mappings: list[MappingEntry] = [],
        current_review_index: int = 0,
    ):
        self.turn_count = turn_count
        self.history = history
        self.phase = phase
        self.mappings = mappings

        # species review count
        self.current_species_review_index = 0

        # mapping file exists
        self.mapping_file_exists = False
        self.mapping = self._load_enzymeml_mapping()

    # try to load EnzymeMLMappings from file
    def _load_enzymeml_mapping(self) -> EnzymeMLMappings:
        try:
            self.mapping_file_exists = True
            return EnzymeMLMappings.load_from_file()
        except FileNotFoundError:
            self.mapping_file_exists = False
            return EnzymeMLMappings()

    async def dispatch(
        self, user_input: str, websocket: Optional[WebSocket] = None
    ) -> dict:
        """Single entry point for all user interactions"""
        self.turn_count += 1
        self.history.append({"role": "user", "content": user_input})

        # Update metadata
        self.mapping.metadata.user_interactions = self.turn_count
        if self.mapping.metadata.original_user_input is None:
            self.mapping.metadata.original_user_input = user_input

        try:
            if self.phase == ConversationPhase.DISCOVERY:
                return await self._run_all_agents(user_input, websocket)
            elif self.phase == ConversationPhase.AGENT_REVIEW:
                return await self._handle_agent_review(user_input, websocket)
            elif self.phase == ConversationPhase.SPECIES_ANALYSIS:
                return await self._run_species_analysis(websocket)
            elif self.phase == ConversationPhase.SPECIES_TRAVERSAL_REVIEW:
                return await self._handle_species_traversal_review(
                    user_input, websocket
                )
            elif self.phase == ConversationPhase.FINALIZATION:
                return self._generate_final_document()
            elif self.phase == ConversationPhase.EXISTING_MAPPING_CHOICE:
                return await self._handle_existing_mapping_choice(user_input, websocket)

            return {"type": "error", "content": "Unknown phase"}
        except Exception as e:
            logger.error(f"Error in evaluate: {str(e)}")
            return {"type": "error", "content": f"Error: {str(e)}"}

    async def _run_all_agents(
        self, user_input: str, websocket: Optional[WebSocket] = None
    ) -> dict:
        """Run all agents in parallel, then start reviewing results"""
        self.original_user_input = user_input  # Store for potential reruns

        # Check if existing mapping file exists first
        if self.mapping_file_exists:
            logger.info("Existing mapping file found, asking user for preference")
            # Call mapping file checker agent
            result = await Runner.run(
                starting_agent=mapping_file_checker_agent, input=user_input
            )

            # Switch to existing mapping choice phase
            self.phase = ConversationPhase.EXISTING_MAPPING_CHOICE

            return {
                "type": "final",
                "content": result.final_output,
            }

        # Define all agents to run
        agents = [
            small_molecule_agent,
            # protein_agent,
            measurement_agent,
        ]

        # Run all agents in parallel
        logger.info(f"Running {len(agents)} agents in parallel")
        tasks = [Runner.run(starting_agent=agent, input=user_input) for agent in agents]
        results = await asyncio.gather(*tasks)

        # Create mapping entries with agent instances for potential reruns
        self.mappings = []
        for agent, result in zip(agents, results):
            logger.debug(f"Building mapping entry for {agent.name}")
            self.mappings.append(
                MappingEntry(
                    object_name=agent.name,
                    report=result.final_output,
                )
            )
        logger.debug("MappingEntries created")

        logger.info(f"All {len(agents)} agents completed. Starting review phase.")

        # Move to review phase and present first result
        self.phase = ConversationPhase.AGENT_REVIEW
        self.current_review_index = 0

        return self._format_current_agent_review()

    async def _run_all_agents_without_existing_check(self, user_input: str) -> dict:
        """Run all agents in parallel without checking for existing mapping file"""
        logger.info("Running all agents in parallel (no existing file check)")

        # Define all agents to run
        agents = [
            small_molecule_agent,
            # protein_agent,
            measurement_agent,
        ]

        # Run all agents in parallel
        logger.info(f"Running {len(agents)} agents in parallel")
        tasks = [Runner.run(starting_agent=agent, input=user_input) for agent in agents]
        results = await asyncio.gather(*tasks)

        # Create mapping entries with agent instances for potential reruns
        self.mappings = []
        for agent, result in zip(agents, results):
            self.mappings.append(
                MappingEntry(
                    object_name=agent.name,
                    report=result.final_output,
                )
            )

        logger.info(f"All {len(agents)} agents completed. Starting review phase.")

        # Move to review phase and present first result
        self.phase = ConversationPhase.AGENT_REVIEW
        self.current_review_index = 0

        return self._format_current_agent_review()

    async def _handle_agent_review(
        self, user_input: str, websocket: Optional[WebSocket] = None
    ) -> dict:
        """Handle user feedback on current agent's results"""
        if self.current_review_index >= len(self.mappings):
            # All agents reviewed, save and automatically run species analysis
            self._save_mappings_to_document()
            self.phase = ConversationPhase.SPECIES_ANALYSIS
            return await self._run_species_analysis(websocket)

        current = self.mappings[self.current_review_index]
        user_input_lower = user_input.lower().strip()

        if any(
            word in user_input_lower
            for word in ["approve", "yes", "good", "ok", "correct"]
        ):
            logger.debug(f"User approves {current.object_name}")
            # User approves - move to next agent
            current.status = MappingStatus.APPROVED
            current.user_feedback = user_input  # Store user feedback
            self.current_review_index += 1

            logger.debug(f"Adding {current.object_name} to EnzymeML document")
            # Add to EnzymeML document
            self.mapping.add_object_mapping(
                object_type=current.object_name,
                status=current.status.value,  # Convert enum to string literal
                report=current.report,
                user_feedback=current.user_feedback,
            )

            # Send confirmation message
            progress_msg = f"✅ **{current.object_name}** approved! ({self.current_review_index}/{len(self.mappings)} agents reviewed)"
            await self._send_intermediate_message(websocket, progress_msg)

            if self.current_review_index >= len(self.mappings):
                # All agents reviewed, save and automatically run species analysis
                self._save_mappings_to_document()
                self.phase = ConversationPhase.SPECIES_ANALYSIS

                await self._send_working_message(
                    websocket,
                    "🎉 All agents reviewed! Checking how species are organized in the measurements...",
                )

                # Run species analysis and return results directly
                return await self._run_species_analysis(websocket)
            else:
                # Format next agent for review and return directly
                return self._format_current_agent_review()

        elif any(word in user_input_lower for word in ["reject", "no", "wrong", "bad"]):
            # User rejects - mark and move to next agent
            current.status = MappingStatus.REJECTED
            current.user_feedback = user_input  # Store user feedback
            self.current_review_index += 1

            # Add to EnzymeML document
            self.mapping.add_object_mapping(
                object_type=current.object_name,
                status=current.status.value,  # Convert enum to string literal
                report=current.report,
                user_feedback=current.user_feedback,
            )

            # Send confirmation message
            progress_msg = f"❌ **{current.object_name}** rejected. ({self.current_review_index}/{len(self.mappings)} agents reviewed)"
            await self._send_intermediate_message(websocket, progress_msg)

            if self.current_review_index >= len(self.mappings):
                # All agents reviewed, save and automatically run species analysis
                self._save_mappings_to_document()
                self.phase = ConversationPhase.SPECIES_ANALYSIS

                await self._send_working_message(
                    websocket, "🎉 All agents reviewed! Running species analysis..."
                )

                # Run species analysis and return results directly
                return await self._run_species_analysis(websocket)
            else:
                # Format next agent for review and return directly
                return self._format_current_agent_review()

        elif (
            any(
                word in user_input_lower
                for word in ["clarify", "clarification", "rerun", "retry", "fix"]
            )
            or len(user_input) > 20
        ):
            # User wants clarification - rerun current agent with feedback
            return await self._rerun_current_agent_with_clarification(user_input)

        else:
            # Short feedback - treat as clarification
            return await self._rerun_current_agent_with_clarification(user_input)

    async def _rerun_current_agent_with_clarification(
        self, user_clarification: str
    ) -> dict:
        """Rerun the current agent with user clarification"""
        current = self.mappings[self.current_review_index]
        logger.info(
            f"Rerunning {current.object_name} with clarification: {user_clarification}"
        )

        # Include previous results so agent knows what it already found correctly
        previous_results = self._format_agent_results_content(current)

        clarified_input = f"""{self.original_user_input}

Previous results from {current.object_name}:
{previous_results}

User clarification: {user_clarification}

Please preserve all correct mappings from the previous results and address the clarification."""

        try:
            # Rerun the specific agent
            result = await Runner.run(
                starting_agent=AGENTS[current.object_name], input=clarified_input
            )

            # Update the mapping entry
            current.report = result.final_output
            current.status = MappingStatus.PENDING  # Reset to pending for re-review

            # Present updated results
            return {
                "type": "final",
                "content": f"🔄 **{current.object_name} rerun complete** with your feedback.\n\n{self._format_agent_results_content(current)}",
            }

        except Exception as e:
            logger.error(f"Error rerunning agent {current.object_name}: {str(e)}")
            return {
                "type": "error",
                "content": f"Error rerunning {current.object_name}: {str(e)}",
            }

    def _format_current_agent_review(self) -> dict:
        """Format current agent results for user review"""
        if self.current_review_index >= len(self.mappings):
            return {"type": "error", "content": "No more agents to review"}

        current = self.mappings[self.current_review_index]
        content = self._format_agent_results_content(current)

        return {"type": "final", "content": content}

    def _format_agent_results_content(self, mapping_entry: MappingEntry) -> str:
        """Format agent results content"""
        current = mapping_entry
        report = current.report

        # Format the mapping report in a user-friendly way
        content_parts = [
            f"## {current.object_name} Mapping Results",
            f"**Agent**: {current.object_name}",
            f"**Progress**: {self.current_review_index + 1}/{len(self.mappings)} agents",
            "",
        ]

        # Add found mappings
        if hasattr(report, "mappings") and report.mappings:
            content_parts.append("### ✅ Found Mappings:")
            for mapping in report.mappings:
                content_parts.append(
                    f"- `{mapping.obj_attr_name}` ↔ `{mapping.node_attr.node_name}.{mapping.node_attr.node_attr}`"
                )
            content_parts.append("")

        # Add ambiguous mappings
        if hasattr(report, "ambiguous_mappings") and report.ambiguous_mappings:
            content_parts.append("### ⚠️ Ambiguous Mappings:")
            for mapping in report.ambiguous_mappings:
                content_parts.append(
                    f"- `{mapping.obj_attr_name}` ↔ `{mapping.node_attr.node_name}.{mapping.node_attr.node_attr}` (needs clarification)"
                )
            content_parts.append("")

        # Add missing mandatory
        if hasattr(report, "missing_mandatory") and report.missing_mandatory:
            content_parts.append("### ❌ Missing Mandatory Mappings:")
            for missing in report.missing_mandatory:
                content_parts.append(f"- `{missing}`")
            content_parts.append("")

        # Add user instructions
        content_parts.extend(
            [
                "**Please respond with:**",
                "- `yes` - Accept these mappings and continue",
                "- `no` - Reject these mappings and continue",
                "- Provide specific feedback to rerun this agent with clarification",
                "",
                "**Example clarifications:**",
                '- "Look for enzyme_id instead of protein_name"',
                "- \"The substrate concentration is in the column 'initial_conc'\"",
                '- "Use the REACTION_DETAILS for pH and temperature"',
            ]
        )

        return "\n".join(content_parts)

    async def _run_species_analysis(
        self, websocket: Optional[WebSocket] = None
    ) -> dict:
        """Run species distinguisher and move to finalization"""
        logger.info("Running species analysis")

        approved_mappings = [
            m for m in self.mappings if m.status == MappingStatus.APPROVED
        ]

        # Format approved mappings for species agent
        species_context = []
        for mapping in approved_mappings:
            if mapping.report.mappings:
                for m in mapping.report.mappings:
                    species_context.append(
                        f"{mapping.object_name}.{m.obj_attr_name} ↔ {m.node_attr.node_name}.{m.node_attr.node_attr}"
                    )

        logger.debug("known context", species_context)
        species_input = f"""
        Execute your job.
        Message from previous agent:
        ```
        We already know mappings from the following agents:
        {chr(10).join(species_context[:10])}
        ```
        User conversation history: ```{self._get_recent_history()}```
        """

        logger.debug(f"sending species input: {species_input}")

        result = await Runner.run(species_distinguisher_agent, species_input)
        report: SpeciesTraversalReport = result.final_output

        logger.info(f"Found {len(report.species)} species")

        # Extract species traversals for individual review
        # Handle case where result is a list containing SpeciesTraversalReport
        self.mapping.measurement_species = report.species

        if not report.species:
            # No species traversals found, skip to finalization
            logger.info("No species traversals found, moving to finalization")
            self.phase = ConversationPhase.FINALIZATION
            return {
                "type": "final",
                "content": "⚠️ **No species traversals found** in the analysis. Moving to final document generation...",
            }

        # Move to individual species traversal review
        logger.info("Moving to species traversal review phase")
        self.phase = ConversationPhase.SPECIES_TRAVERSAL_REVIEW
        self.current_species_review_index = 0

        traversal_summary = []
        for i, t in enumerate(report.species):
            try:
                # Simplified name extraction - just use category and species ID
                name = f"{t.category.title()} ({t.species_id.node_name}.{t.species_id.node_attr})"
                traversal_summary.append(f"{i + 1}. {name}")
            except Exception as e:
                logger.error(f"Error formatting traversal {i}: {e}")
                traversal_summary.append(f"{i + 1}. {t.category.title()} species")

        overview_content = f"""## 🧬 Species Analysis Complete!

**Found {len(report.species)} species individal species:**
{chr(10).join(traversal_summary)}

Let's review each species traversal individually for approval.

---

{self._format_current_species_traversal_review()}"""

        logger.info(
            f"Returning species analysis overview content (length: {len(overview_content)})"
        )
        logger.debug(f"Overview content: {overview_content[:200]}...")

        return {
            "type": "final",
            "content": overview_content,
        }

    async def _handle_species_traversal_review(
        self, user_input: str, websocket: Optional[WebSocket] = None
    ) -> dict:
        """Handle user feedback on current species traversal"""
        if self.current_species_review_index >= len(self.mapping.measurement_species):
            # All species traversals reviewed, move to finalization
            self.phase = ConversationPhase.FINALIZATION
            progress_msg = "🎉 **All species traversals reviewed!** Generating final mapping document..."

            # Generate final document and return combined result
            final_result = self._generate_final_document()
            final_result["content"] = f"{progress_msg}\n\n{final_result['content']}"
            return final_result

        current_traversal = self.mapping.measurement_species[
            self.current_species_review_index
        ]
        user_input_lower = user_input.lower().strip()

        if any(
            word in user_input_lower
            for word in ["approve", "yes", "good", "ok", "correct"]
        ):
            # User approves current species traversal
            self.current_species_review_index += 1

            # Send confirmation message
            progress_msg = f"✅ **Species traversal {self.current_species_review_index}/{len(self.mapping.measurement_species)} approved!**"
            await self._send_intermediate_message(websocket, progress_msg)

            if self.current_species_review_index >= len(
                self.mapping.measurement_species
            ):
                # All traversals reviewed
                self.phase = ConversationPhase.FINALIZATION

                await self._send_working_message(
                    websocket,
                    "🎉 All species traversals reviewed! Generating final mapping document...",
                )

                # Generate final document and return directly
                return self._generate_final_document()
            else:
                # Show next species traversal directly
                return {
                    "type": "final",
                    "content": self._format_current_species_traversal_review(),
                }

        elif any(word in user_input_lower for word in ["reject", "no", "wrong", "bad"]):
            # User rejects current species traversal
            self.current_species_review_index += 1

            # Send confirmation message
            progress_msg = f"❌ **Species traversal {self.current_species_review_index}/{len(self.mapping.measurement_species)} rejected.**"
            await self._send_intermediate_message(websocket, progress_msg)

            if self.current_species_review_index >= len(
                self.mapping.measurement_species
            ):
                # All traversals reviewed
                self.phase = ConversationPhase.FINALIZATION

                await self._send_working_message(
                    websocket,
                    "🎉 All species traversals reviewed! Generating final mapping document...",
                )

                # Generate final document and return directly
                return self._generate_final_document()
            else:
                # Show next species traversal directly
                return {
                    "type": "final",
                    "content": self._format_current_species_traversal_review(),
                }

        elif (
            any(
                word in user_input_lower
                for word in ["clarify", "clarification", "rerun", "retry", "fix"]
            )
            or len(user_input) > 20
        ):
            # User wants clarification - rerun species analysis
            return await self._rerun_species_analysis_with_clarification(user_input)

        else:
            # Short feedback - treat as clarification
            return await self._rerun_species_analysis_with_clarification(user_input)

    async def _rerun_species_analysis_with_clarification(
        self, user_clarification: str
    ) -> dict:
        """Rerun species analysis with user clarification"""
        logger.info(
            f"Rerunning species analysis with clarification: {user_clarification}"
        )

        approved_mappings = [
            m for m in self.mappings if m.status == MappingStatus.APPROVED
        ]

        # Format approved mappings for species agent
        species_context = []
        for mapping in approved_mappings:
            if hasattr(mapping.report, "mappings") and mapping.report.mappings:
                for m in mapping.report.mappings:
                    species_context.append(
                        f"{mapping.object_name}.{m.obj_attr_name} <-> {m.node_attr.node_name}.{m.node_attr.node_attr}"
                    )

        # Prepare input with clarification
        clarified_input = f"""
        Execute your job.
        Message from previous agent:
        ```
        We already know mappings from the following agents:
        {chr(10).join(species_context[:10])}
        ```
        User conversation history: ```{self._get_recent_history()}```
        
        User clarification for species analysis: {user_clarification}
        """

        logger.debug(
            f"Re-running species analysis with clarification: {clarified_input}"
        )

        try:
            # Rerun species analysis with clarification
            result = await Runner.run(species_distinguisher_agent, clarified_input)
            agent_report: SpeciesTraversalReport = result.final_output

            # Extract updated species traversals for review
            # Handle case where result is a list containing SpeciesTraversalReport
            self.mapping.measurement_species = agent_report.species

            # Reset review state and show first traversal
            self.current_species_review_index = 0

            if not self.mapping.measurement_species:
                return {
                    "type": "final",
                    "content": "🔄 **Species analysis rerun complete** - No species traversals found. Moving to final document generation...",
                }

            # Show overview and first species traversal
            traversal_summary = []
            for i, t in enumerate(self.mapping.measurement_species):
                try:
                    name = f"{t.category.title()} ({t.species_id.node_name}.{t.species_id.node_attr})"
                    traversal_summary.append(f"- {i + 1}. {name}")
                except Exception as e:
                    logger.error(f"Error formatting traversal {i}: {e}")
                    traversal_summary.append(f"- {i + 1}. {t.category.title()} species")

            overview_content = f"""🔄 **Species analysis rerun complete** with your feedback.

**Found {len(self.mapping.measurement_species)} species traversal(s):**
{chr(10).join(traversal_summary)}

---

{self._format_current_species_traversal_review()}"""

            return {
                "type": "final",
                "content": overview_content,
            }

        except Exception as e:
            logger.error(f"Error rerunning species analysis: {str(e)}")
            return {
                "type": "error",
                "content": f"Error rerunning species analysis: {str(e)}",
            }

    def _format_current_species_traversal_review(self) -> str:
        """Format current species traversal for user review"""
        if self.current_species_review_index >= len(self.mapping.measurement_species):
            return "No more species traversals to review."

        current = self.mapping.measurement_species[self.current_species_review_index]
        progress = f"({self.current_species_review_index + 1}/{len(self.mapping.measurement_species)})"

        content_parts = [
            f"## Species Review {progress}",
            "",
            f"### 🧬 {current.category.title()} Species",
            "",
            "**Traversal Pattern:**",
            "```cypher",
            f"{current.traversal}",
            "```",
            "",
            "**Species Identification:**",
            f"- Species ID: `{current.species_id.node_name}.{current.species_id.node_attr}`",
        ]

        # Add initial concentration info if available
        if current.initial:
            content_parts.extend(
                [
                    f"- Initial concentration: `{current.initial.node_name}.{current.initial.node_attr}`"
                ]
            )

        # Add data unit info if available
        if current.data_unit:
            content_parts.extend(
                [
                    f"- Data unit: `{current.data_unit.node_name}.{current.data_unit.node_attr}`"
                ]
            )

        content_parts.append("")

        # Add measurement data information
        if current.has_observed_data:
            content_parts.extend(
                [
                    "### 📊 **Measurement Data: FOUND** ✅",
                    "",
                    "**Data Query Strategy:**",
                    "```cypher",
                    f"{current.has_observed_data.query}",
                    "```",
                    f"**Explanation:** {current.has_observed_data.explanation}",
                    "",
                ]
            )
        else:
            content_parts.extend(
                [
                    "### 📊 **Measurement Data: NOT FOUND** ❌",
                    "",
                    "No time-course measurement data was found for this species.",
                    "",
                ]
            )

        # Add user instructions
        content_parts.extend(
            [
                "**Please respond with:**",
                "- `yes` - Accept this species traversal and continue",
                "- `no` - Reject this species traversal and continue",
                "- Provide specific feedback to rerun the species analysis with clarification",
                "",
                "**Example clarifications:**",
                f'- "Use {current.species_id.node_name}.name instead of {current.species_id.node_attr}"',
                '- "Look for measurement data in a different relationship"',
                f'- "This should be a {("small_molecule" if current.category == "protein" else "protein")} instead"',
            ]
        )

        return "\n".join(content_parts)

    def _save_mappings_to_document(self) -> None:
        """Save all processed mappings to the EnzymeML document"""
        for mapping in self.mappings:
            if mapping.status != MappingStatus.PENDING:
                self.mapping.add_object_mapping(
                    object_type=mapping.object_name,
                    status=mapping.status.value,  # Convert enum to string literal
                    report=mapping.report,
                    user_feedback=mapping.user_feedback,
                )

    def _generate_final_document(self) -> dict:
        """Generate final summary and save the document"""
        # Update completion status
        self.mapping.metadata.completion_status = "completed"

        # Save to file
        saved_filepath = self.mapping.save_to_file()

        approved = [m for m in self.mappings if m.status == MappingStatus.APPROVED]
        rejected = [m for m in self.mappings if m.status == MappingStatus.REJECTED]

        # Count species info directly from the species analysis
        species_count = len(self.mapping.measurement_species)

        final_content = f"""
# Interactive Mapping Session Complete

## Summary
- **Total agents run**: {len(self.mappings)}
- **Approved mappings**: {len(approved)}
- **Rejected mappings**: {len(rejected)}
- **Species traversals found**: {species_count}
- **User interactions**: {self.turn_count}

## Approved Agent Results
{chr(10).join([f"- **{m.object_name}**: {m.object_name} mappings approved" for m in approved])}

## Rejected Agent Results  
{chr(10).join([f"- **{m.object_name}**: {m.object_name} mappings rejected" for m in rejected])}

## Species Analysis Results
{f"Found {species_count} species traversal(s) in the analysis" if species_count > 0 else "No species traversals found"}

## 📄 **Mapping Document Saved**
Your complete EnzymeML mapping document has been saved to:
`{saved_filepath}`

This document contains:
- All approved attribute mappings
- Session metadata and user feedback
- Species analysis results
- Ready for programmatic EnzymeML extraction

---
**Session complete!** You can start a new conversation for another mapping task.
"""

        return {"type": "final", "content": final_content}

    async def _handle_existing_mapping_choice(
        self, user_input: str, websocket: Optional[WebSocket] = None
    ) -> dict:
        """Handle user's choice to use existing mappings or run new ones."""
        user_input_lower = user_input.lower().strip()

        if "use existing" in user_input_lower or any(
            word in user_input_lower for word in ["use", "existing", "load", "keep"]
        ):
            logger.info("User chose to use existing mappings.")
            self.phase = ConversationPhase.FINALIZATION

            content = """✅ **Using existing mapping file!**

Loading your previous EnzymeML mapping results and generating the final document..."""

            # Generate final document with existing data
            final_result = self._generate_final_document()
            final_result["content"] = f"{content}\n\n{final_result['content']}"
            return final_result

        elif "create new" in user_input_lower or any(
            word in user_input_lower
            for word in ["new", "fresh", "start", "create", "overwrite"]
        ):
            logger.info("User chose to create new mappings.")

            # Send working message to indicate analysis is starting
            await self._send_working_message(
                websocket,
                "✅ **Creating new mapping!**\n\nRunning all mapping agents...",
            )

            # Reset the EnzymeML mappings to start fresh
            self.mapping = EnzymeMLMappings()
            self.mapping_file_exists = False

            # Switch back to discovery phase to run all agents
            self.phase = ConversationPhase.DISCOVERY

            # Run all agents from scratch and return results directly
            return await self._run_all_agents_without_existing_check(
                self.original_user_input
            )

        else:
            # User input doesn't match expected options, ask for clarification
            return {
                "type": "final",
                "content": """❓ **Please choose one of the options:**

- Type `use existing` to load and use the previous mapping results
- Type `create new` to start fresh and create a new mapping

What would you like to do?""",
            }

    def _get_recent_history(self, n_messages: int = 3) -> str:
        """Get recent conversation history"""
        recent = self.history[-n_messages:] if n_messages else self.history
        return " | ".join([f"{h['role']}: {h['content'][:50]}..." for h in recent])

    async def _send_intermediate_message(
        self, websocket: Optional[WebSocket], content: str
    ):
        """Helper method to send intermediate status messages via WebSocket"""
        if websocket:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "status",  # Changed from "intermediate" to "status"
                        "content": content,
                    }
                )
            )
            # Small delay to ensure message ordering
            await asyncio.sleep(1)

    async def _send_working_message(self, websocket: Optional[WebSocket], content: str):
        """Helper method to send working status that indicates more messages are coming"""
        if websocket:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "working",  # Indicates system is working, more messages coming
                        "content": content,
                    }
                )
            )
            # Small delay to ensure message ordering
            await asyncio.sleep(1)


@router.websocket("/llm_chat")
async def llm_chat(websocket: WebSocket):
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")

        chat_state = ChatState()

        # Send welcome message
        await websocket.send_text(
            json.dumps(
                {
                    "type": "intermediate",
                    "content": "Hello! I'm your **Interactive EnzymeML Mapping Assistant**.\n\nI'll run all mapping agents in parallel, then walk you through each result for approval.\n\nPlease describe your mapping task to get started.",
                }
            )
        )

        while True:
            try:
                # Receive message
                raw = await websocket.receive_text()
                user_message = json.loads(raw)["content"]

                # Always call dispatch method
                logger.info(f"Conversation phase: {chat_state.phase}")
                logger.info(f"Dispatching user message: {user_message}")
                response = await chat_state.dispatch(user_message, websocket)

                # Send response
                await websocket.send_text(json.dumps(response))
                logger.info(f"Sent: {response['type']}")

            except WebSocketDisconnect:
                logger.info("Client disconnected")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {str(e)}")
                await websocket.send_text(
                    json.dumps({"type": "error", "content": "Invalid message format"})
                )
            except Exception as e:
                logger.error(f"Error in message loop: {str(e)}")
                await websocket.send_text(
                    json.dumps({"type": "error", "content": f"Error: {str(e)}"})
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected during setup")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        logger.info("WebSocket connection closed")
