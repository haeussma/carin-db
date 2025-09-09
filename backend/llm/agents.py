from enum import Enum

from agents import Agent
from pydantic import BaseModel, Field
from pyenzyme import Measurement, MeasurementData, Protein, SmallMolecule

from .models import (
    MappingReport,
    SpeciesTraversalReport,
)
from .tools import GRAPH_SCHEMA_EXAMPLE, clean_json_ld, execute_query, get_graph_schema

MODEL = "o4-mini"


# Enum for existing mapping choices
class ExistingMappingChoice(str, Enum):
    USE_EXISTING = "use_existing"
    CREATE_NEW = "create_new"
    MAP_DATA = "map_data"


OBJECT_MAPPING_PROCEDURE = """
Procedure:
1. Call the `get_graph_schema` tool to get the graph schema
2. See if you can find mappings from the database to the object.
3. In case of ambiguity, call the `biochemistry_semantics_agent` to clarify the mapping.
4. If the mapping is still ambiguous, mark it as such.

Rules:
- Focus on `required` properties.
- Optional properties should not be filled if not certain that the mapping is correct.
"""

simple_test_agent = Agent(
    name="simple_test_agent",
    instructions="""
        You are a test agent.
        You don't want to give long answers.
        So you only ever answer with three words.
    """,
    model="gpt-3.5-turbo",
    output_type=str,
)

cypher_fixer_agent = Agent(
    name="cypher_fixer_agent",
    instructions="""
        You are a cypher fixer agent.
        You are given a cypher query that is not working.
        You need to fix it.
        Only return the fixed cypher query. No other text.
    """,
    model=MODEL,
    output_type=str,
    tools=[get_graph_schema],
)

mapping_file_checker_agent = Agent(
    name="mapping_file_checker_agent",
    instructions="""
        You are a mapping file checker agent.
        
        Your job is to inform the user that an existing EnzymeML mapping file has been found
        and ask them to choose between three options:
        
        1. Use the existing mapping to generate the final EnzymeML document directly
        2. Create a new mapping from scratch (overwriting the existing file)  
        3. Use the existing mapping to extract data from the database
        
        Always respond in a clear, friendly format. Keep your response concise but informative.
        Use this exact format:
        
        "## 📄 Existing Mapping Found!
        
        I found an existing EnzymeML mapping file with previous results.
        
        **Please choose one of the following options:**
        
        1. **Use existing mapping** - Load the previous mapping and generate the final EnzymeML document
        2. **Create new mapping** - Start fresh and create a new mapping (this will overwrite the existing file)  
        3. **Map data with existing** - Use the existing mapping to extract data from your database
        
        **Please respond with:**
        - `use existing` for option 1
        - `create new` for option 2  
        - `map data` for option 3
        
        What would you like to do?"
    """,
    model="gpt-3.5-turbo",
    output_type=str,
)

mapping_choice_parser_agent = Agent(
    name="mapping_choice_parser_agent",
    instructions="""
        You are a choice parser agent that analyzes user input to determine their intended action
        regarding existing EnzymeML mapping files.
        
        Your job is to parse user input and return one of three choices:
        - "use_existing": User wants to use existing mappings to generate final document
        - "create_new": User wants to create new mappings from scratch  
        - "map_data": User wants to use existing mappings to extract/map data
        
        Look for these patterns:
        - use_existing: "use existing", "load", "keep", "existing mapping", "previous", "1"
        - create_new: "create new", "new", "fresh", "start over", "overwrite", "2"
        - map_data: "map data", "extract", "use mapping", "query", "get data", "3"
        
        If the input is ambiguous or doesn't clearly match any option, return "unclear".
        
        Return only one of: "use_existing", "create_new", "map_data", or "unclear"
    """,
    model="gpt-3.5-turbo",
    output_type=str,
)

biochemistry_semantics_agent = Agent(
    name="biochemistry_semantics_agent",
    instructions="""
        You are a seasoned biochemist assisting mapping agents.
        They may ask whether a database term is semantically equivalent to a term in a target data model.
        For example, 'enzyme' and 'protein' are equivalent; 'protein name' and 'database name' are not.
        Be pragmatic: accept close matches when exact ones are unavailable (e.g., using 'id' as 'name' if needed).
        Keep responses short and precise.
    """,
    model=MODEL,
)


# ── Data Assessment Agents (is atomic information for EnzymeML present in the database)
small_molecule_agent = Agent(
    name="SmallMolecule",
    instructions=f"""
        You are a specialized agent for mapping database information to SmallMolecule objects.
        Here is the description of the SmallMolecule object:
        ```
        {clean_json_ld(SmallMolecule.model_json_schema())}
        ```
        {OBJECT_MAPPING_PROCEDURE}

    """,
    model=MODEL,
    output_type=MappingReport,
    tools=[
        get_graph_schema,
        biochemistry_semantics_agent.as_tool(
            tool_name="biochemistry_semantics_agent",
            tool_description="A tool to clarify ambiguous mappings.",
        ),
    ],
)


protein_agent = Agent(
    name="Protein",
    instructions=f"""
        You are a specialized agent for finding semantic matches between the description of an enzyme and the nodes and relationships in a Neo4j database that should be mapped to an Enzyme object.
        Your job is to check if in the Graph all mandatory information infomation is present to map to an instance of Enzyme.
        Here is the description of the Enzyme object:
        ```
        {clean_json_ld(Protein.model_json_schema())}
        ```
        {OBJECT_MAPPING_PROCEDURE}
    """,
    model=MODEL,
    tools=[get_graph_schema],
    output_type=MappingReport,
)


measurement_agent = Agent(
    name="Measurement",
    instructions=f"""
        You are a specialized agent for finding finding the correct mappings for a Measurement object.
        The object contains a nested object of MeasurementData. Don't consider it. That's the job of another agent.
        Here is the description of the Measurement object:
        ```
        {clean_json_ld(Measurement.model_json_schema())}
        ```
        {OBJECT_MAPPING_PROCEDURE}
    """,
    model=MODEL,
    tools=[get_graph_schema],
    output_type=MappingReport,
)

measurement_data_agent = Agent(
    name="MeasurementData",
    instructions=f"""
        You are a specialized agent for finding the correct mappings for a MeasurementData object.
        Here is the description of the MeasurementData object:
        ```
        {clean_json_ld(MeasurementData.model_json_schema())}
        ```
        {OBJECT_MAPPING_PROCEDURE}
    """,
    model=MODEL,
    tools=[get_graph_schema],
    output_type=MappingReport,
)

mapping_report_agent = Agent(
    name="MappingReport",
    instructions="""
        You are a specialized agent for writing a message to the user notifying them of the `MappingReport`s
        and asking them to clarify the mappings if neccessary.
        Write a list of instructions to the user to clarify the mappings if neccessary.
        Also ask the user if any of the mappings are incorrect.
        If there isn't any ambiguity, or incorrect mapping for an object,
        dont show the corresponding lvl 3 headers.

        Write your message in the following format:
            ```
            # EnzymeML Mapping Report
            <YOUR 3 SENTENCE SUMMARY>
            ## <object_name>
            ### ✅ Found Mappings
                - <attribute_name> <-> <node_name>.<attribute_name>
                - ...
            ### ⚠️ Ambiguous Mappings
                - <attribute_name> <-> <node_name>.<attribute_name>
                - ...
            ### ❌ Missing Mandatory Properties
                - <attribute_name>
                - ...
            ## Please clarify the following mappings:
            <LIST OF TASKS TO THE USER TO CLARIFY>
            ```
    """,
    model=MODEL,
    output_type=str,
)

cypher_translator_agent = Agent(
    name="CypherTranslator",
    instructions=(
        "You are a specialized agent for translating natural language queries into Cypher queries. "
        "You can only use nodes and relationships that are allowed by the graph schema. "
        "Otherwise the query will fail."
        "You need to call the `get_graph_schema` tool first to get the graph schema on which you can base query design."
        "When writing the MATCH clause, use the full node names from the graph schema. E.g. instead of MATCH (e:ExampleNode) use MATCH (ExampleNode:ExampleNode). "
        "return only the Cypher query, do not include any other text. "
    ),
    tools=[get_graph_schema],
    model=MODEL,
)


data_analysis_agent = Agent(
    name="data_analysis_agent",
    instructions="""
        You are a specialized agent for biochemical data analysis.

        You always need follow the following steps:
        1. Rephrase the question into a Cypher query. Consult the `Cypher_Translator_Agent`.
        2. Execute the query and get the data by calling the `execute_query` tool to get the data.
        3. Create a report based on the data.
            a. Summerize the data in a concise way.
            b. Answer specific questions about the data asked by the user.

        Note:
        - The report needs to fully be founded on the data. Do not come up with analysis and conclusion if they are not backed by the data.
        - Don't make up data. If you don't have the data, say so.
    """,
    tools=[
        cypher_translator_agent.as_tool(
            tool_name="cypher_translator_agent",
            tool_description="A tool for translating natural language queries into Cypher queries.",
        ),
        execute_query,
    ],
    model=MODEL,
)


question_dispatcher_agent = Agent(
    name="QuestionDispatcher",
    instructions="""
        You are a specialized agent that dispatches tasks to the appropriate agents
        based on the user's question.

        There following agents are available:
        - Cypher_Translator_Agent
            - Call this agent if the user does not specifically ask to analyze data.
            - Call this agent for phrases similar or equivalent to:
                - Give me the data for ...
                - I need ...
                - Is there data for ...
        - Data_Analysis_Agent
            - Call this agent if the user asks to analyze data.
            - Call this agent for phrases similar or equivalent to:
                - Analyze the data for ...
                - Look into my data ...
                - Is there a connection between ...
                - Do you spot ...
                - Give me a summary of ...
    """,
    model=MODEL,
    handoffs=[cypher_translator_agent, data_analysis_agent],
)


species_distinguisher_agent = Agent(
    name="species_distinguisher_agent",
    instructions=f"""
    ROLE ▸ You are an Biochemisty Expert. You analyze an **unknown** property graph (Neo4j-like) that encodes:
        reactions, measurements, proteins/enzymes, and small-molecule species.
        The Graph has 2 meta concepts of nodes:
        - Species: a species is a protein or small molecule.
            - E.g., protein, small molecule, enzyme, biocatalyst, etc.
        - Measurement / Reaction / Preparation: a measurement or reaction is a collection of data points.
            - E.g., Measurement, Reaction, preparation, settings, etc.

        These two meta concepts can interact with each other in different ways, altering the context of a species
        to its observation / measurement / reaction / preparation.

        Your Job is to find unique traversals in this graph descibing the interaction between the meta concepts.
        Here is the graph schema:
        ```
        {GRAPH_SCHEMA_EXAMPLE}
        ```

        The idea is to finde unique queries that are used by a different agent to build cypher queries to extract the necessary data.

        Therefore, you need to find meaningfull traversals that allow to extract the different species that were involved in a
        reaction or measurement. For a species to be listed it always needs to have a clearly identifiable initial concentration and unit.
        Otherwise leave it out.
        If there is besides the initial concentration also information about the measurement values (besides initial concentration) and
        corresponding time values and resective concentration, add this information to the `has_observed_data` field. of the SpeciesTraversal.

        The goal of each traversal is to find initial concentrations for each species that is present in one measurement / reaction / preparation.
        So keep a look out for protrties or relationships like "enzyme_concentration", "initial_enzyme", "substrate_conc", cosubstrate_conc, "product_conc", etc.

    Account for user notes: these are important to understand the graph if there are any.

    OUTPUT ▸ Return a `SpeciesTraversalReport` matching the schema exactly.
    Fill out a reasoned debug explanation for each traversal candidate why it was rejected.
    Because the output does not contain everything that i would like to see there!!!
    """,
    model=MODEL,
    output_type=SpeciesTraversalReport,
)

data_extraction_agent = Agent(
    name="DataExtractionAgent",
    instructions=f"""
    You are a specialized agent for generating programmatic Cypher queries to extract specific data from a Neo4j graph database.

    **Your Role:**
    - Parse user requests for data extraction.
    - Use provided query instructions on what to extract.
    - Generate structured Cypher queries that can be executed error free.

    Here is the graph schema for which the query is executed:
    ```
    {GRAPH_SCHEMA_EXAMPLE}
    ```

    **Output Requirements:**
    - Generate StructuredCypherQuery objects with:
      - Clean Cypher query using proper node names
      - Field mappings showing how query results map to object attributes
      - Clear description of what the query does
    - Use the exact node and attribute names from the mappings
    - Include WHERE clauses for any filtering requested by user

    **Cypher Query Rules:**
    - Use exact node and attribute names from the schema and user instructions.
    - Pay close attention to the graph schema it is case sensitive!
    - Design the query in such a way the the resulting table names match the names from the user instructions.
    - RETURN ONLY THE CYPHER QUERY, DO NOT INCLUDE ANY OTHER TEXT.
    - Pay specieal attention to get the correct casing for edges. They might not always be all uppercase!
    """,
    model=MODEL,
    output_type=str,
    # tools=[get_graph_schema],
)

data_mapping_agent = Agent(
    name="data_mapping_agent",
    instructions="""
        You are a data mapping specialist that uses existing EnzymeML mappings to extract data from the database.
        
        Your role is to:
        1. Analyze the provided existing EnzymeML mapping file 
        2. Understand what data the user wants to extract/map
        3. Use the existing mappings to generate appropriate Cypher queries
        4. Guide the user through the data extraction process
        
        You have access to existing mappings that show how EnzymeML objects map to database nodes and attributes.
        Use these mappings to construct queries that extract the requested data in the proper EnzymeML format.
        
        Always:
        - Explain what data can be extracted based on the existing mappings
        - Ask the user to specify what data they want to extract  
        - Provide clear Cypher queries when requested
        - Format results in a user-friendly way
        
        Be helpful and guide the user through the data extraction process step by step.
    """,
    model=MODEL,
    output_type=str,
    tools=[get_graph_schema, execute_query],
)


class MeasurementTopology(BaseModel):
    measurement_id_query: str = Field(
        description="A cypher query that returns the internal Neo4j node IDs of all nodes that contain *measured* measurement data."
    )
    additional_info: str = Field(
        description="Additional information how the measured data is connected to the species."
    )


measurement_topology_agent = Agent(
    name="measurement_topology_agent",
    instructions="""
        You are a specialized agent for analyzing the topology of a measurement.
        You are given infromation where to find measured data in the graph.
        Additionally you are provided with information for which subset of the graph data is needed.

        Your job is to create a `MeasurementTopology` object that describes the topology of the measurement.
        The purpose of the `MeasurementTopology` object is to yield a cypher query that leads to the node ids
        with the measured data which are a subset of the entire graph.

        Verfiy against the graph schema that the query is valid.

        <graph_schema>
        {GRAPH_SCHEMA_EXAMPLE}
        </graph_schema>
    """,
    model=MODEL,
    output_type=MeasurementTopology,
    # tools=[get_graph_schema],
)


if __name__ == "__main__":
    import asyncio
    import json

    from agents import Runner

    from .models import EnzymeMLMappings

    # Load existing mappings
    mappings = EnzymeMLMappings.load_from_file()

    # Prepare input with user request and relevant mappings
    user_request = "Extract all small molecules in reaction with id r23"

    small_molecule_mappings = mappings.small_molecule.model_dump()

    agent_input = f"""
    User Request: {user_request}

    Relevant Mappings:
    {json.dumps(small_molecule_mappings, indent=2)}
    """

    # Run the agent
    result = asyncio.run(Runner.run(data_extraction_agent, agent_input))
    query_report: str = result.final_output

    # Use the generated queries
    print(query_report)
