# App Config

## Root Objects

### AppConfig

- databases
    - Type: DatabaseInfo[]
    - Description: A list of databases to use for the app
- openai_api_key
    - Type: string
    - Description: The API key for the OpenAI API

### DatabaseInfo

- **name**
    - Type: string
    - Description: The name of the database
- **uri**
    - Type: string
    - Description: The URI of the database
- **username**
    - Type: string
    - Description: The username of the database
- **password**
    - Type: string
    - Description: The password of the database
- sheet_model
    - Type: SheetModel
    - Description: The sheet model for the database
- graph_model
    - Type: GraphModel
    - Description: The graph model for the database

## Sheet Model

### SheetModel

- sheets
    - Type: Sheet[]
    - Description: A list of sheets in the database
- sheet_connections
    - Type: SheetConnection[]
    - Description: A list of connections between sheets
- sheet_references
    - Type: SheetReferences[]
    - Description: A list of references between sheets

### Sheet

- name
    - Type: string
    - Description: The name of the sheet
- columns
    - Type: Column[]
    - Description: A list of columns in the sheet

### Column

- name
    - Type: string
    - Description: The name of the column
- data_type
    - Type: string
    - Description: The data type of the column

### SheetConnection

- source_sheet_name
    - Type: string
    - Description: The name of the source sheet
- target_sheet_name
    - Type: string
    - Description: The name of the target sheet
- edge_name
    - Type: string
    - Description: The name of the edge connecting the sheets
- key
    - Type: string
    - Description: The key field used to connect the sheets

### SheetReferences

- source_sheet_name
    - Type: string
    - Description: The name of the source sheet
- source_column_name
    - Type: string
    - Description: The name of the column in the source sheet
- target_sheet_name
    - Type: string
    - Description: The name of the target sheet
- target_column_name
    - Type: string
    - Description: The name of the column in the target sheet

## Graph Model

### GraphModel

- nodes
    - Type: Node[]
    - Description: A list of nodes in the graph
- relationships
    - Type: Relationship[]
    - Description: A list of relationships between nodes in the graph

### Attribute

- name
    - Type: string
    - Description: The name of the attribute
- data_type
    - Type: string
    - Description: The data type of the attribute

### Node

- name
    - Type: string
    - Description: The name of the node
- attributes
    - Type: Attribute[]
    - Description: A list of attributes associated with the node

### Relationship

- source
    - Type: string
    - Description: The source node of the relationship
- name
    - Type: string
    - Description: The name of the relationship
- targets
    - Type: string[]
    - Description: The target nodes of the relationship
