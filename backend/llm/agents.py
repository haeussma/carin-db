from agents import Agent
from pyenzyme import Measurement, MeasurementData, Protein, SmallMolecule

from .models import EvaluationReport, MappingReport
from .tools import execute_query, get_graph_schema, remove_jsonld_fields

MODEL = "gpt-4.1-2025-04-14"

biochemistry_semantics_agent = Agent(
    name="biochemistry_semantics_agent",
    instructions="""
        You are a specialized agent for finding semantic matches between different biochemical terms .
        Other agents may approach you if uncertain wheter a term in its instructions matches another term. 
        E.g. if an name of a protein is equivalent to the database name of a protein. (obviously not). But e.g. a `enzyme` is equivalent to a `protein`.
        or a small molecule to a chemical substance or compound.
        Keep your answer short and concise.
    """,
    model=MODEL,
)


# ── Data Assessment Agents (is atomic information for EnzymeML present in the database)
small_molecule_agent = Agent(
    name="small_molecule_agent",
    instructions=f"""
        You are a specialized agent for mapping database information to SmallMolecule objects. 
        Here is the description of the SmallMolecule object:
        ```
        {remove_jsonld_fields(SmallMolecule.model_json_schema())}
        ```
        You need to call the `get_graph_schema` tool to get the graph schema 
        and then use the `execute_query` tool to get the data you need to map. 
        You can only use information that is present in the database results. 
        For the ID field, you can use an abbreviation of the molecule name (e.g., 'glc' for 'glucose').
        Never fill out the fields `@id`, `@type`, or `@context`.
        If multiple molecules are asked for, you need to return a list of SmallMolecule objects. Adjust the cypher query accordingly.
    """,
    model=MODEL,
    output_type=MappingReport,
    tools=[get_graph_schema, execute_query],
)


protein_agent = Agent(
    name="protein_agent",
    instructions=f"""
        You are a specialized agent for finding semantic matches between the description of an enzyme and the nodes and relationships in a Neo4j database that should be mapped to an Enzyme object.
        Your job is to check if in the Graph all mandatory information infomation is present to map to an instance of Enzyme.
        Here is the description of the Enzyme object:
        ```
        {remove_jsonld_fields(Protein.model_json_schema())}
        ```
        If you cannot find a match for the `id` field, you can use the content that fits the `name` field for the `id` field.
        So this isnt't a show stopper.
    """,
    model=MODEL,
    tools=[get_graph_schema],
    output_type=MappingReport,
)


measurement_agent = Agent(
    name="measurement_agent",
    instructions=f"""
        You are a specialized agent for finding finding the correct mappings for a Measurement object.
        The object contains a nested object of MeasurementData. Don't consider it. That's the job of another agent.
        Here is the description of the Measurement object:
        ```
        {remove_jsonld_fields(Measurement.model_json_schema())}
        ```
        If you cannot find a match for the `id` field, you can use the content that fits the `name` field. And vice versa.
    """,
    model=MODEL,
    tools=[get_graph_schema],
    output_type=MappingReport,
)

measurement_data_agent = Agent(
    name="measurement_data_agent",
    instructions=f"""
        You are a specialized agent for finding the correct mappings for a MeasurementData object.
        Here is the description of the MeasurementData object:
        ```
        {remove_jsonld_fields(MeasurementData.model_json_schema())}
        ```
    """,
    model=MODEL,
    tools=[get_graph_schema],
    output_type=MappingReport,
)

mapping_evaluation_agent = Agent(
    name="mapping_evaluation_agent",
    instructions="""
        You are a specialized agent for evaluating the reports of the individual agents.
        Your job is to decide if the mapping are reasonable.
        You can change the reports if neccessary in accordance with the biochemistry_semantics_agent.
        You can also get the graph schema to understand the graph using the `get_graph_schema` tool.
        You need to evaluate the mapping and return your final report.
    """,
    model=MODEL,
    output_type=EvaluationReport,
    tools=[
        biochemistry_semantics_agent.as_tool(
            tool_name="biochemistry_semantics_agent",
            tool_description="A tool to clarify ambiguous mappings.",
        ),
        get_graph_schema,
    ],
)

# ── Data Analysis Agents


cypher_translator_agent = Agent(
    name="cypher_translator_agent",
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
    name="question_dispatcher_agent",
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
