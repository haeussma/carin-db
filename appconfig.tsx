import * as D from 'io-ts/Decoder';
import { isLeft } from "fp-ts/Either";

// Generic validate function
export function validate<T>(codec: D.Decoder<unknown, T>, value: unknown): T {
  const result = codec.decode(value);
  if (isLeft(result)) {
    throw new Error(D.draw(result.left));
  }
  return result.right;
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
**/
export interface AppConfig extends JsonLd {
  databases?: DatabaseInfo[] | null;
  openai_api_key?: string | null;
}

export const AppConfigCodec = D.lazy("AppConfig", () => D.struct({
    databases: D.array(DatabaseInfoCodec),
    openai_api_key: D.nullable(D.string),
}));


/**
    * @param name - The name of the database
    * @param uri - The URI of the database
    * @param username - The username of the database
    * @param password - The password of the database
    * @param sheet_model - The sheet model for the database
    * @param graph_model - The graph model for the database
**/
export interface DatabaseInfo extends JsonLd {
  name: string;
  uri: string;
  username: string;
  password: string;
  sheet_model?: SheetModel | null;
  graph_model?: GraphModel | null;
}

export const DatabaseInfoCodec = D.lazy("DatabaseInfo", () => D.struct({
    name: D.string,
    uri: D.string,
    username: D.string,
    password: D.string,
    sheet_model: D.nullable(SheetModelCodec),
    graph_model: D.nullable(GraphModelCodec),
}));


/**
    * @param sheets - A list of sheets in the database
    * @param sheet_connections - A list of connections between sheets
    * @param sheet_references - A list of references between sheets
**/
export interface SheetModel extends JsonLd {
  sheets?: Sheet[] | null;
  sheet_connections?: SheetConnection[] | null;
  sheet_references?: SheetReferences[] | null;
}

export const SheetModelCodec = D.lazy("SheetModel", () => D.struct({
    sheets: D.array(SheetCodec),
    sheet_connections: D.array(SheetConnectionCodec),
    sheet_references: D.array(SheetReferencesCodec),
}));


/**
    * @param name - The name of the sheet
    * @param columns - A list of columns in the sheet
**/
export interface Sheet extends JsonLd {
  name?: string | null;
  columns?: Column[] | null;
}

export const SheetCodec = D.lazy("Sheet", () => D.struct({
    name: D.nullable(D.string),
    columns: D.array(ColumnCodec),
}));


/**
    * @param name - The name of the column
    * @param data_type - The data type of the column
**/
export interface Column extends JsonLd {
  name?: string | null;
  data_type?: string | null;
}

export const ColumnCodec = D.lazy("Column", () => D.struct({
    name: D.nullable(D.string),
    data_type: D.nullable(D.string),
}));


/**
    * @param source_sheet_name - The name of the source sheet
    * @param target_sheet_name - The name of the target sheet
    * @param edge_name - The name of the edge connecting the sheets
    * @param key - The key field used to connect the sheets
**/
export interface SheetConnection extends JsonLd {
  source_sheet_name?: string | null;
  target_sheet_name?: string | null;
  edge_name?: string | null;
  key?: string | null;
}

export const SheetConnectionCodec = D.lazy("SheetConnection", () => D.struct({
    source_sheet_name: D.nullable(D.string),
    target_sheet_name: D.nullable(D.string),
    edge_name: D.nullable(D.string),
    key: D.nullable(D.string),
}));


/**
    * @param source_sheet_name - The name of the source sheet
    * @param source_column_name - The name of the column in the source sheet
    * @param target_sheet_name - The name of the target sheet
    * @param target_column_name - The name of the column in the target sheet
**/
export interface SheetReferences extends JsonLd {
  source_sheet_name?: string | null;
  source_column_name?: string | null;
  target_sheet_name?: string | null;
  target_column_name?: string | null;
}

export const SheetReferencesCodec = D.lazy("SheetReferences", () => D.struct({
    source_sheet_name: D.nullable(D.string),
    source_column_name: D.nullable(D.string),
    target_sheet_name: D.nullable(D.string),
    target_column_name: D.nullable(D.string),
}));


/**
    * @param nodes - A list of nodes in the graph
    * @param relationships - A list of relationships between nodes in the graph
**/
export interface GraphModel extends JsonLd {
  nodes?: Node[] | null;
  relationships?: Relationship[] | null;
}

export const GraphModelCodec = D.lazy("GraphModel", () => D.struct({
    nodes: D.array(NodeCodec),
    relationships: D.array(RelationshipCodec),
}));


/**
    * @param name - The name of the attribute
    * @param data_type - The data type of the attribute
**/
export interface Attribute extends JsonLd {
  name?: string | null;
  data_type?: string | null;
}

export const AttributeCodec = D.lazy("Attribute", () => D.struct({
    name: D.nullable(D.string),
    data_type: D.nullable(D.string),
}));


/**
    * @param name - The name of the node
    * @param attributes - A list of attributes associated with the node
**/
export interface Node extends JsonLd {
  name?: string | null;
  attributes?: Attribute[] | null;
}

export const NodeCodec = D.lazy("Node", () => D.struct({
    name: D.nullable(D.string),
    attributes: D.array(AttributeCodec),
}));


/**
    * @param source - The source node of the relationship
    * @param name - The name of the relationship
    * @param targets - The target nodes of the relationship
**/
export interface Relationship extends JsonLd {
  source?: string | null;
  name?: string | null;
  targets?: string[] | null;
}

export const RelationshipCodec = D.lazy("Relationship", () => D.struct({
    source: D.nullable(D.string),
    name: D.nullable(D.string),
    targets: D.array(D.string),
}));