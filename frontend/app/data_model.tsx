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
  databases?: Database[] | null;
  openai_api_key?: string | null;
}

export const AppConfigCodec = D.lazy("AppConfig", () => D.struct({
  databases: D.array(DatabaseCodec),
  openai_api_key: D.nullable(D.string),
}));


/**
    * @param name - The name of the database
    * @param uri - The URI of the database
    * @param username - The username of the database
    * @param password - The password of the database
    * @param graph_model - The graph model for the database
**/
export interface Database extends JsonLd {
  name?: string | null;
  uri?: string | null;
  username?: string | null;
  password?: string | null;
  graph_model?: GraphModel | null;
}

export const DatabaseCodec = D.lazy("Database", () => D.struct({
  name: D.nullable(D.string),
  uri: D.nullable(D.string),
  username: D.nullable(D.string),
  password: D.nullable(D.string),
  graph_model: D.nullable(GraphModelCodec),
}));


/**
    * @param sheet_connections - A list of connections between sheets
    * @param sheet_references - A list of references between sheets
**/
export interface GraphModel extends JsonLd {
  sheet_connections?: SheetConnection[] | null;
  sheet_references?: SheetReference[] | null;
}

export const GraphModelCodec = D.lazy("GraphModel", () => D.struct({
  sheet_connections: D.array(SheetConnectionCodec),
  sheet_references: D.array(SheetReferenceCodec),
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
export interface SheetReference extends JsonLd {
  source_sheet_name?: string | null;
  source_column_name?: string | null;
  target_sheet_name?: string | null;
  target_column_name?: string | null;
}

export const SheetReferenceCodec = D.lazy("SheetReference", () => D.struct({
  source_sheet_name: D.nullable(D.string),
  source_column_name: D.nullable(D.string),
  target_sheet_name: D.nullable(D.string),
  target_column_name: D.nullable(D.string),
}));