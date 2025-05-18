// A trivial validate function that simply casts the value.
// (Replace with proper type guards if runtime validation is needed.)
export function validate<T>(value: unknown): T {
  return value as T;
}

// JSON-LD Types
export interface JsonLdContext {
  [key: string]: any;
}

export interface JsonLd {
  '@context'?: JsonLdContext;
  '@id'?: string;
  '@type'?: string;
}

// App Config Type definitions
/**
 * @param databases - A list of databases to use for the app
 * @param openai_api_key - The API key for the OpenAI API
 */
export interface AppConfig extends JsonLd {
  databases?: DatabaseInfo[] | null;
  openai_api_key?: string | null;
}

// Database Info
/**
 * @param uri - The URI of the database
 * @param username - The username of the database
 * @param password - The password of the database
 * @param sheet_model - The sheet model for the database
 */
export interface DatabaseInfo extends JsonLd {
  uri: string;
  username: string;
  password: string;
  sheet_model?: SheetModel | null;
}

// Sheet Model
/**
 * @param sheets - A list of sheets in the database
 * @param sheet_connections - A list of connections between sheets
 * @param sheet_references - A list of references between sheets
 */
export interface SheetModel extends JsonLd {
  sheets: Sheet[];
  sheet_connections: SheetConnection[];
  sheet_references: SheetReference[];
}

// Sheet
/**
 * @param name - The name of the sheet
 * @param columns - A list of columns in the sheet
 */
export interface Sheet extends JsonLd {
  name: string;
  columns: Column[];
}

// Column
/**
 * @param name - The name of the column
 * @param data_type - The data type of the column
 */
export interface Column extends JsonLd {
  name: string;
  data_type: string;
}

// Sheet Connection
/**
 * @param source_sheet_name - The name of the source sheet
 * @param target_sheet_name - The name of the target sheet
 * @param edge_name - The name of the edge connecting the sheets
 * @param key - The key field used to connect the sheets
 */
export interface SheetConnection extends JsonLd {
  source_sheet_name: string;
  target_sheet_name: string;
  edge_name: string;
  key: string;
}

// Sheet References
/**
 * @param source_sheet_name - The name of the source sheet
 * @param source_column_name - The name of the column in the source sheet
 * @param target_sheet_name - The name of the target sheet
 * @param target_column_name - The name of the column in the target sheet
 */
export interface SheetReference extends JsonLd {
  source_sheet_name?: string | null;
  source_column_name?: string | null;
  target_sheet_name?: string | null;
  target_column_name?: string | null;
}

// Graph Model
/**
 * @param nodes - A list of nodes in the graph
 * @param relationships - A list of relationships between nodes in the graph
 */
export interface GraphModel extends JsonLd {
  nodes?: Node[] | null;
  relationships?: Relationship[] | null;
}

// Attribute
/**
 * @param name - The name of the attribute
 * @param data_type - The data type of the attribute
 */
export interface Attribute extends JsonLd {
  name?: string | null;
  data_type?: string | null;
}

// Node
/**
 * @param name - The name of the node
 * @param attributes - A list of attributes associated with the node
 */
export interface Node extends JsonLd {
  name?: string | null;
  attributes?: Attribute[] | null;
}

// Relationship
/**
 * @param source - The source node of the relationship
 * @param name - The name of the relationship
 * @param targets - The target nodes of the relationship
 */
export interface Relationship extends JsonLd {
  source?: string | null;
  name?: string | null;
  targets?: string[] | null;
}
