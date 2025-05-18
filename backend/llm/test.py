from pydantic_ai import Agent
from pyenzyme import SmallMolecule

# Define the output model with optional fields


# Create the agent with the specified output type
agent = Agent(
    model="openai:gpt-4o",
    output_type=SmallMolecule,
    system_prompt="Extract small molecule information from the input text. Never make up information!",
)

# Example input where all fields are present
input_text_full = "glucose (glc) is a small molecule. with constant concentration over time. the inchikey is DGLZLUUXXVUPTL-UHFFFAOYSA-N and a synonym is glc or sugar"
result_full = agent.run_sync(input_text_full)
print(result_full.output)
# Output: name='John Doe' age=30 email='john.doe@example.com'

# Example input with missing optional fields
input_text_partial = "glucose (glc) is a small molecule."
result_partial = agent.run_sync(input_text_partial)
print(result_partial.output)
# Output: name='Jane Smith' age=None email=None
