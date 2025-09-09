from dataclasses import dataclass
from typing import List, Optional

from loguru import logger

from backend.models.graph_model import GraphModel
from backend.models.model import Sheet
from backend.services.database import Database


@dataclass
class SchemaMismatch:
    """Represents a schema mismatch between spreadsheet and existing graph."""

    sheet_name: str
    mismatch_type: str  # "missing_sheet", "missing_column", "type_mismatch"
    expected: Optional[str] = None  # What exists in graph
    actual: Optional[str] = None  # What's in spreadsheet
    column_name: Optional[str] = None
    message: str = ""


@dataclass
class CompatibilityResult:
    """Result of schema compatibility check."""

    is_compatible: bool
    mismatches: List[SchemaMismatch]
    can_auto_resolve: bool  # If mismatches can be automatically resolved
    resolution_summary: str


class SchemaCompatibilityChecker:
    """Checks if a new spreadsheet is compatible with existing graph schema."""

    def __init__(self, db: Database):
        self.db = db

    def check_compatibility(self, new_sheets: List[Sheet]) -> CompatibilityResult:
        """
        Check if new spreadsheet sheets are compatible with existing graph model.

        Args:
            new_sheets: List of sheets from the new spreadsheet

        Returns:
            CompatibilityResult with compatibility status and any issues
        """
        logger.info("Starting schema compatibility check")

        # Get current graph structure
        current_graph = self.db.get_db_structure

        # If no existing nodes, everything is compatible
        if not current_graph.nodes:
            logger.info("No existing graph structure, all sheets are compatible")
            return CompatibilityResult(
                is_compatible=True,
                mismatches=[],
                can_auto_resolve=True,
                resolution_summary="No existing schema - will create new structure",
            )

        mismatches = []

        # Check each sheet against existing nodes
        for sheet in new_sheets:
            mismatches.extend(self._check_sheet_compatibility(sheet, current_graph))

        # Determine if mismatches can be auto-resolved
        can_auto_resolve = all(
            mismatch.mismatch_type in ["missing_column", "missing_sheet"]
            for mismatch in mismatches
        )

        # Create resolution summary
        resolution_summary = self._create_resolution_summary(mismatches)

        return CompatibilityResult(
            is_compatible=len(mismatches) == 0,
            mismatches=mismatches,
            can_auto_resolve=can_auto_resolve,
            resolution_summary=resolution_summary,
        )

    def _check_sheet_compatibility(
        self, sheet: Sheet, graph: GraphModel
    ) -> List[SchemaMismatch]:
        """Check a single sheet against the graph model."""
        mismatches = []

        # Find corresponding graph node
        graph_node = next(
            (node for node in graph.nodes if node.name == sheet.name), None
        )

        if not graph_node:
            # Sheet doesn't exist as node in graph - this is additive, OK
            mismatches.append(
                SchemaMismatch(
                    sheet_name=sheet.name,
                    mismatch_type="missing_sheet",
                    message=f"Sheet '{sheet.name}' will create new node type in graph",
                )
            )
            return mismatches

        # Check columns against node attributes
        existing_attrs = {attr.attr_name for attr in graph_node.attributes}
        new_columns = {col.name for col in sheet.columns}

        # Find missing columns (exist in graph but not in sheet)
        missing_in_sheet = existing_attrs - new_columns
        for missing_col in missing_in_sheet:
            mismatches.append(
                SchemaMismatch(
                    sheet_name=sheet.name,
                    mismatch_type="missing_column",
                    expected=missing_col,
                    actual=None,
                    column_name=missing_col,
                    message=f"Column '{missing_col}' exists in graph but missing in sheet '{sheet.name}'",
                )
            )

        # Find new columns (exist in sheet but not in graph)
        new_in_sheet = new_columns - existing_attrs
        for new_col in new_in_sheet:
            mismatches.append(
                SchemaMismatch(
                    sheet_name=sheet.name,
                    mismatch_type="missing_column",
                    expected=None,
                    actual=new_col,
                    column_name=new_col,
                    message=f"New column '{new_col}' will be added to existing '{sheet.name}' nodes",
                )
            )

        # Could add type checking here if you track types in graph model
        # For now, Neo4j is flexible with property types

        return mismatches

    def _create_resolution_summary(self, mismatches: List[SchemaMismatch]) -> str:
        """Create human-readable summary of how mismatches will be resolved."""
        if not mismatches:
            return "No schema conflicts - proceeding with upload"

        summary_parts = []

        # Group by type
        missing_sheets = [m for m in mismatches if m.mismatch_type == "missing_sheet"]
        missing_columns = [m for m in mismatches if m.mismatch_type == "missing_column"]

        if missing_sheets:
            sheet_names = [m.sheet_name for m in missing_sheets]
            summary_parts.append(
                f"Will create new node types: {', '.join(sheet_names)}"
            )

        if missing_columns:
            by_sheet: dict[str, dict[str, list[str]]] = {}
            for m in missing_columns:
                if m.sheet_name not in by_sheet:
                    by_sheet[m.sheet_name] = {"new": [], "missing": []}

                if m.actual:  # New column in sheet
                    by_sheet[m.sheet_name]["new"].append(m.column_name)  # type: ignore
                else:  # Missing column in sheet
                    by_sheet[m.sheet_name]["missing"].append(m.column_name)  # type: ignore

            for sheet_name, changes in by_sheet.items():
                if changes["new"]:
                    summary_parts.append(
                        f"Will add new properties to '{sheet_name}': {', '.join(changes['new'])}"
                    )
                if changes["missing"]:
                    summary_parts.append(
                        f"⚠️  Missing properties in '{sheet_name}': {', '.join(changes['missing'])} (will be null)"
                    )

        return "; ".join(summary_parts)
