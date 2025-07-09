from typing import Any

from agents import function_tool
from loguru import logger

from ..services.database import get_db

# ---- Agent Tools ----


@function_tool
async def get_graph_schema():
    """Get the graph schema with information about labels, rel-types, property keys."""
    logger.debug("AGENT TOOL CALL: get_graph_schema")
    return get_db().get_graph_info_dict


@function_tool
async def execute_query(query: str):
    """Execute a Cypher query and return the results.
    You can only use cypher queries that are allowed by the graph schema.
    """
    logger.debug(f"AGENT TOOL CALL: execute_query with query: {query}")
    return get_db().execute_query(query)


# ---- Helper Functions ----


def clean_json_ld(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove JSON-LD specific fields
    - references
    - ld_id
    - ld_type
    - ld_context
    from the properties of the schema.
    Args:
        schema: The schema dictionary to clean

    Returns:
        A new dictionary with JSON-LD fields removed
    """

    if not schema["properties"]:
        return schema

    to_remove = ("references", "ld_id", "ld_type", "ld_context")
    cleaned: dict[str, Any] = {"properties": {}}

    for prop in schema["properties"]:
        if prop in to_remove:
            continue
        cleaned["properties"][prop] = schema["properties"][prop]

    return cleaned


GRAPH_SCHEMA_EXAMPLE = """
{
  "sheets": [
    {
      "name": "Molecule",
      "columns": [
        {
          "name": "molecule_id",
          "data_type": "float"
        },
        {
          "name": "NAME",
          "data_type": "str"
        },
        {
          "name": "solvent",
          "data_type": "str"
        },
        {
          "name": "formulation",
          "data_type": "str"
        },
        {
          "name": "storage_temperature",
          "data_type": "float"
        },
        {
          "name": "storage_temperature_unit",
          "data_type": "str"
        },
        {
          "name": "cas_id",
          "data_type": "str"
        },
        {
          "name": "supplier",
          "data_type": "str"
        },
        {
          "name": "purity_percentual",
          "data_type": "str"
        }
      ]
    },
    {
      "name": "Biocatalyst",
      "columns": [
        {
          "name": "EXPRESSION_ID",
          "data_type": "str"
        },
        {
          "name": "catalyst_self_produced",
          "data_type": "bool"
        },
        {
          "name": "expressed_enzyme",
          "data_type": "str"
        },
        {
          "name": "Production_organism",
          "data_type": "str"
        },
        {
          "name": "production_strain",
          "data_type": "str"
        },
        {
          "name": "Medium",
          "data_type": "str"
        },
        {
          "name": "Volume_medium",
          "data_type": "float"
        },
        {
          "name": "Volume_unit",
          "data_type": "str"
        },
        {
          "name": "Antibiotic",
          "data_type": "str"
        },
        {
          "name": "Antibiotic_concentration",
          "data_type": "float"
        },
        {
          "name": "Antibiotic_unit",
          "data_type": "str"
        },
        {
          "name": "Temperature",
          "data_type": "float"
        },
        {
          "name": "Temperature_unit",
          "data_type": "str"
        },
        {
          "name": "cell_density_at_induction",
          "data_type": "str"
        },
        {
          "name": "density_unit",
          "data_type": "str"
        },
        {
          "name": "induction_molecule",
          "data_type": "str"
        },
        {
          "name": "induction_molecule_concentration",
          "data_type": "float"
        },
        {
          "name": "induction_molecule_concentration_unit",
          "data_type": "str"
        },
        {
          "name": "duration",
          "data_type": "float"
        },
        {
          "name": "duration_unit",
          "data_type": "str"
        },
        {
          "name": "agitation",
          "data_type": "float"
        },
        {
          "name": "agitation_unit",
          "data_type": "str"
        },
        {
          "name": "sequence_confirmation ",
          "data_type": "bool"
        },
        {
          "name": "cell_disruption_process",
          "data_type": "str"
        },
        {
          "name": "Formulation",
          "data_type": "str"
        },
        {
          "name": "Purification_strategy",
          "data_type": "str"
        },
        {
          "name": "was_immobilized",
          "data_type": "bool"
        },
        {
          "name": "Visible_Band_Gel_protein",
          "data_type": "bool"
        },
        {
          "name": "Concentration_unit",
          "data_type": "str"
        },
        {
          "name": "concentration_determination_method",
          "data_type": "str"
        },
        {
          "name": "storage_temperature",
          "data_type": "float"
        },
        {
          "name": "storage_temperature_unit",
          "data_type": "str"
        },
        {
          "name": "volume_unit",
          "data_type": "str"
        }
      ]
    },
    {
      "name": "Enzyme",
      "columns": [
        {
          "name": "ENZYME_ID",
          "data_type": "str"
        },
        {
          "name": "database_id",
          "data_type": "str"
        },
        {
          "name": "database_name",
          "data_type": "str"
        },
        {
          "name": "Cofactor",
          "data_type": "str"
        },
        {
          "name": "sequence_length",
          "data_type": "float"
        },
        {
          "name": "gene_id",
          "data_type": "str"
        },
        {
          "name": "database_gene",
          "data_type": "str"
        },
        {
          "name": "source_organism",
          "data_type": "str"
        },
        {
          "name": "plasmid",
          "data_type": "str"
        },
        {
          "name": "N-terminal_fusion",
          "data_type": "str"
        },
        {
          "name": "C-terminal_fusion",
          "data_type": "str"
        },
        {
          "name": "sequence",
          "data_type": "str"
        },
        {
          "name": "sequenc_level",
          "data_type": "str"
        }
      ]
    },
    {
      "name": "Reaction",
      "columns": [
        {
          "name": "REACTION_ID",
          "data_type": "str"
        },
        {
          "name": "has_protein",
          "data_type": "str"
        },
        {
          "name": "vessel",
          "data_type": "str"
        },
        {
          "name": "has_substrate",
          "data_type": "str"
        },
        {
          "name": "has_product",
          "data_type": "str"
        },
        {
          "name": "has_cosubstrate",
          "data_type": "str"
        },
        {
          "name": "temperature",
          "data_type": "float"
        },
        {
          "name": "unit temperature",
          "data_type": "str"
        },
        {
          "name": "ph",
          "data_type": "float"
        },
        {
          "name": "Buffer",
          "data_type": "str"
        },
        {
          "name": "volume",
          "data_type": "float"
        },
        {
          "name": "unit_volume",
          "data_type": "str"
        },
        {
          "name": "agitation",
          "data_type": "float"
        },
        {
          "name": "unit_agitation",
          "data_type": "str"
        },
        {
          "name": "measured_molecule",
          "data_type": "str"
        }
      ]
    },
    {
      "name": "Measurement",
      "columns": [
        {
          "name": "has_reaction",
          "data_type": "str"
        },
        {
          "name": "enzyme_concentration",
          "data_type": "float"
        },
        {
          "name": "enzyme_unit",
          "data_type": "str"
        },
        {
          "name": "substrate_concentration",
          "data_type": "float"
        },
        {
          "name": "cosubstrate_concentration ",
          "data_type": "float"
        },
        {
          "name": "product_initial",
          "data_type": "float"
        },
        {
          "name": "concentration_unit",
          "data_type": "str"
        },
        {
          "name": "wavelength",
          "data_type": "float"
        },
        {
          "name": "wavelength_unit",
          "data_type": "str"
        },
        {
          "name": "activity",
          "data_type": "float"
        },
        {
          "name": "activity_stddev",
          "data_type": "float"
        },
        {
          "name": "activity_unit",
          "data_type": "str"
        },
        {
          "name": "measurment_time",
          "data_type": "float"
        },
        {
          "name": "time_unit",
          "data_type": "str"
        },
        {
          "name": "product_measured",
          "data_type": "float"
        },
        {
          "name": "measurement_type",
          "data_type": "str"
        },
        {
          "name": "product_concentration",
          "data_type": "float"
        }
      ]
    }
  ],
  "sheet_connections": [],
  "sheet_references": [
    {
      "source_sheet_name": "Biocatalyst",
      "source_column_name": "expressed_enzyme",
      "target_sheet_name": "Enzyme",
      "target_column_name": "ENZYME_ID"
    },
    {
      "source_sheet_name": "Measurement",
      "source_column_name": "has_reaction",
      "target_sheet_name": "Reaction",
      "target_column_name": "REACTION_ID"
    },
    {
      "source_sheet_name": "Reaction",
      "source_column_name": "has_protein",
      "target_sheet_name": "Biocatalyst",
      "target_column_name": "EXPRESSION_ID"
    },
    {
      "source_sheet_name": "Reaction",
      "source_column_name": "has_substrate",
      "target_sheet_name": "Molecule",
      "target_column_name": "NAME"
    },
    {
      "source_sheet_name": "Reaction",
      "source_column_name": "has_product",
      "target_sheet_name": "Molecule",
      "target_column_name": "NAME"
    },
    {
      "source_sheet_name": "Reaction",
      "source_column_name": "has_cosubstrate",
      "target_sheet_name": "Molecule",
      "target_column_name": "NAME"
    }
  ]
}
"""
