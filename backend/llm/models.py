import uuid

# Add these imports at the top if not already present
from datetime import datetime
from typing import Literal, Union

from pydantic import BaseModel, Field

# ---- Mapping Between Objects and Database Nodes ----


class NodeAttribute(BaseModel):
    """A node attribute that is mapped to an object attribute."""

    node_name: str = Field(description="The name of the node.")
    node_attr: str = Field(description="The attribute name of the node.")


class AttributeMapping(BaseModel):
    """A mapping of an object attribute to a Neo4j database node attribute."""

    obj_attr_name: str = Field(
        description="The attribute name of the object (mapping target)."
    )
    node_attr: NodeAttribute = Field(
        description="The node attribute that is mapped to the object attribute (mapping source)."
    )


class MappingReport(BaseModel):
    """Report on the mapping of a small molecule to a Neo4j database."""

    object_name: str = Field(
        description="The name of the object to map to (mapping target).",
    )
    mappings: list[AttributeMapping] = Field(
        description="List of individual attribute mappings that were clearly found in the graph.",
        default_factory=list,
    )
    ambiguous_mappings: list[AttributeMapping] = Field(
        description="List of individual attribute mappings that were found in the graph but are ambiguous.",
        default_factory=list,
    )
    agent_name: str = Field(
        description="The name of the agent that filled the report.",
    )
    missing_mandatory: list[str] = Field(
        description="List of mandatory attributes for which no mapping was found.",
        default_factory=list,
    )


class MeasurementMappingReport(MappingReport):
    """Report on the mapping of a measurement to a Neo4j database."""

    object_name: str = Field(
        description="The name of the object to map to (mapping target).",
    )
    measurement_data_attributes: list[str] = Field(
        description="List of measurement data attributes that were found in the graph.",
    )
    measured_species_reference_strategy: str = Field(
        description="The way how the information about which species was measured is described in the graph.",
    )


class Instruction(BaseModel):
    """An instruction to the next agent."""

    agent_name: str = Field(
        description="The name of the agent that should follow the instruction.",
    )
    instruction: str = Field(
        description="The instruction to the agent.",
    )


class EvaluationReport(BaseModel):
    """Report on the mapping of a small molecule to a Neo4j database."""

    report: str = Field(
        description="Short summary of the mapping. Mentions fails and ambiguities of the individual agents.",
    )
    ambiguous_instructions: list[Instruction] = Field(
        description="Instructions to the corresponding agents on what is ambiguous and should be calarified. Might contain mapping suggestions.",
    )
    reports: Union[list[MappingReport], None] = Field(
        description="Reports from the individual agents.",
    )
    next_step: Literal["continue", "clarify", "abort"] = Field(
        description="How to proceed. One of 'continue', 'clarify', 'abort'",
    )


class ClarificationRequest(BaseModel):
    """
    A request to the user to resolve ambiguity on one or more fields.
    """

    object_name: str
    ambiguous_keys: list[str] = Field(
        ..., description="List of attribute names that need clarification"
    )
    # a single natural-language question you want the user to answer
    question: str = Field(
        ..., description="Prompt the user to choose or supply the correct value"
    )


# ── primitive recipe & helpers ─────────────────────────────────────────────
class GraphLocator(BaseModel):
    """How to reach a value inside *any* property-graph DB."""

    start: str = Field(
        description="Anchor pattern, e.g. '(m:Measurement)'",
    )
    path: str = Field(
        description="Traversal from `start` to the node/edge holding the value",
    )
    prop: str | None = Field(
        description="Property containing the value (None ⇒ use the whole element)"
    )


class ExtractionRecipe(BaseModel):
    """Declarative step-by-step to fetch & shape a value."""

    source: GraphLocator = Field(
        description="Raw inputs in graph",
    )
    target: str = Field(
        description="EnzymeML field to fill",
    )
    confidence: float = Field(
        description="0–1 confidence",
    )
    notes: str | None = Field(
        description="Heuristics / caveats",
    )


# ── wrapper that can be resolved / ambiguous / missing ────────────────────
class Ambiguous(BaseModel):
    options: list[str] = Field(
        description="Human-readable alternatives",
    )
    reason: str = Field(
        description="Why the agent can’t decide",
    )


class Missing(BaseModel):
    reason: str = Field(
        description="Why the value could not be located",
    )


# ── the plan emitted *per species* ─────────────────────────────────────────
class ExtractionPlan(BaseModel):
    """
    Generic plan describing how to reconstruct one MeasurementData
    object from an arbitrary reaction-measurement KG.
    """

    species_id: ExtractionRecipe | Ambiguous | Missing = Field(
        description="Recipe (or ambiguity/missing) returning `MeasurementData.species_id`",
    )
    data_series: ExtractionRecipe | Ambiguous | Missing = Field(
        description="Recipe for the data vector",
    )
    time_series: ExtractionRecipe | Ambiguous | Missing = Field(
        description="Recipe for the corresponding time vector",
    )
    initial: ExtractionRecipe | Ambiguous | Missing = Field(
        description="Recipe for initial concentration",
    )
    prepared: ExtractionRecipe | Ambiguous | Missing = Field(
        description="Recipe for prepared amount",
    )
    time_unit: ExtractionRecipe | Ambiguous | Missing = Field(
        description="Recipe for the time unit of the time series",
    )
    data_unit: ExtractionRecipe | Ambiguous | Missing = Field(
        description="Recipe for the data unit of the data vector",
    )
    data_type: ExtractionRecipe | Ambiguous | Missing = Field(
        description="Recipe for the data type of the data vector",
    )


class MeasurementDataSpeciesExtractionPlan(BaseModel):
    """Describes the concept how for each species the data is represented in the graph."""

    proteins_recipes: list[ExtractionPlan] = Field(
        description="Generic recipe how to extract `MeasurementData` attributes for proteins",
    )
    proteins_strategy: str = Field(
        description="What topological feature of the graph devides how many proteins are measured",
    )
    small_molecules_recipes: list[ExtractionPlan] = Field(
        description="Generic recipe how to extract `MeasurementData` attributes for small molecules",
    )
    small_molecules_strategy: str = Field(
        description="What topological feature of the graph devides how many small molecules are measured",
    )


class NodeAttributeNotFound(BaseModel):
    """
    A node attribute that was not found in the graph.
    """

    potential_attributes: list[NodeAttribute] = Field(
        description="The potential attributes that could be used to identify the species"
    )


class QueryStrategy(BaseModel):
    """
    A strategy to query the graph for a given species.
    """

    query: str = Field(description="The query to the graph")
    explanation: str = Field(description="A short explanation of the query")


class SpeciesTraversal(BaseModel):
    """
    Summarises how one biochemical 'species class' is wired into the graph.
    A class is defined by a unique path pattern *plus* a node category
    (protein/enzymes vs. small-molecule/chemical).  If both substrate and
    product use HAS_PRODUCT vs. HAS_SUBSTRATE, they become two classes.
    """

    category: Literal["protein", "small_molecule"] = Field(
        description="The category of the species"
    )
    traversal: str = Field(
        description="Cypher of the traversal pattern to connect the measurement and or reaction to the species"
    )
    species_id: NodeAttribute = Field(
        description="The node attribute that uniquely identifies the species"
    )
    initial: NodeAttribute | None = Field(
        description="The node attribute that contains the initial concentration of the species"
    )
    data_unit: NodeAttribute | None = Field(
        description="The node attribute that contains the unit of the data"
    )
    has_observed_data: None | QueryStrategy = Field(
        description="If the species has data that is dependent on another field/node/relationship, describe how to query it. Otherwise None."
    )


class SpeciesTraversalReport(BaseModel):
    """
    A report on the species traversals that were found in the graph.
    """

    species: list[SpeciesTraversal] = Field(
        description="The species traversals that were found in the graph."
    )
    debug: str = Field(
        description="A short debug explanation for each traversal candidate why it was rejected."
    )


# ── EnzymeML Complete Mapping Document ─────────────────────────────────────


class ObjectMapping(BaseModel):
    """Mapping information for a single EnzymeML object type."""

    object_type: str = Field(
        description="Type of EnzymeML object (e.g., 'SmallMolecule', 'Protein', 'Measurement')"
    )
    status: Literal["approved", "rejected", "needs_rerun"] = Field(
        description="User approval status of this mapping"
    )
    attribute_mappings: list[AttributeMapping] = Field(
        description="List of approved attribute mappings for this object",
        default_factory=list,
    )
    ambiguous_mappings: list[AttributeMapping] = Field(
        description="List of mappings that were ambiguous and need clarification",
        default_factory=list,
    )
    missing_mandatory: list[str] = Field(
        description="List of mandatory EnzymeML attributes that couldn't be mapped",
        default_factory=list,
    )
    user_feedback: str | None = Field(
        description="Any user feedback or clarification provided", default=None
    )


class SessionMetadata(BaseModel):
    """Metadata about the mapping session."""

    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this mapping session",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the session was created",
    )
    user_interactions: int = Field(
        description="Number of user interactions during the session", default=0
    )
    original_user_input: str | None = Field(
        description="Original user input that started the mapping process", default=None
    )
    completion_status: Literal["in_progress", "completed", "aborted"] = Field(
        description="Overall status of the mapping session", default="in_progress"
    )


class EnzymeMLMappings(BaseModel):
    """Complete mapping document for an EnzymeML document with all object mappings."""

    # Session metadata
    metadata: SessionMetadata = Field(
        description="Metadata about the mapping session",
        default_factory=SessionMetadata,
    )

    # Individual object mappings
    small_molecule: ObjectMapping | None = Field(
        description="Mapping for SmallMolecule objects",
        default=None,
    )
    protein: ObjectMapping | None = Field(
        description="Mapping for Protein/Enzyme objects",
        default=None,
    )
    measurement: ObjectMapping | None = Field(
        description="Mapping for Measurement objects",
        default=None,
    )
    # Species analysis results
    measurement_species: list[SpeciesTraversal] = Field(
        description="Individual species comprising a measurement", default=[]
    )

    # Summary information
    total_agents_run: int = Field(
        description="Total number of mapping agents executed", default=0
    )
    approved_mappings_count: int = Field(
        description="Number of object mappings that were approved", default=0
    )
    rejected_mappings_count: int = Field(
        description="Number of object mappings that were rejected", default=0
    )

    def add_object_mapping(
        self,
        object_type: str,
        status: Literal["approved", "rejected", "needs_rerun"],
        report: MappingReport,
        user_feedback: str | None = None,
    ) -> None:
        """Add a mapping entry to the appropriate object field."""
        object_mapping = ObjectMapping(
            object_type=object_type,
            status=status,
            attribute_mappings=report.mappings,
            ambiguous_mappings=report.ambiguous_mappings,
            missing_mandatory=report.missing_mandatory,
            user_feedback=user_feedback,
        )

        # Map to appropriate field based on object type
        if object_type == "Protein":
            self.protein = object_mapping
        elif object_type == "SmallMolecule":
            self.small_molecule = object_mapping
        elif object_type == "Measurement":
            self.measurement = object_mapping
        else:
            raise ValueError(
                f"Unknown object type for adding a `ObjectMapping`: {object_type}"
            )

        # Update counts
        self.total_agents_run += 1
        if status == "approved":
            self.approved_mappings_count += 1
        elif status == "rejected":
            self.rejected_mappings_count += 1

    def get_approved_mappings(self) -> dict[str, list[AttributeMapping]]:
        """Get all approved attribute mappings organized by object type."""
        approved: dict[str, list[AttributeMapping]] = {}

        for obj in [
            self.small_molecule,
            self.protein,
            self.measurement,
        ]:
            if obj is not None and obj.status == "approved":
                approved[obj.object_type] = obj.attribute_mappings

        return approved

    def save_to_file(self, filepath: str | None = None) -> str:
        """Save the mapping document to a JSON file."""
        import json
        import os

        if filepath is None:
            filename = "enzymeml_mappings.json"
            filepath = os.path.join("uploads", filename)

        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Save with proper serialization
        with open(filepath, "w") as f:
            json.dump(self.model_dump(), f, indent=2, default=str)

        return filepath

    @classmethod
    def load_from_file(cls) -> "EnzymeMLMappings":
        """Load a mapping document from a JSON file."""
        import json

        filepath = "uploads/enzymeml_mappings.json"

        with open(filepath, "r") as f:
            data = json.load(f)

        return cls.model_validate(data)
