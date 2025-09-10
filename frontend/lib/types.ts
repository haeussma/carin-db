export type ScalarType = "str" | "int" | "float" | "bool" | "timestamp"

export type CaseMode = "sensitive" | "insensitive"
export type OnMissMode = "error" | "skip" | "create"

export interface MultiSpec {
  sep: string
  trim: boolean
  allow_empty: boolean
}

export interface ValueProperty {
  kind: "value"
  name: string
  dtype: ScalarType
  unique: boolean
}

export interface RefProperty {
  kind: "ref"
  name: string
  to: string
  on: string
  edge: string
  multi?: MultiSpec
  case: CaseMode
  on_miss: OnMissMode
  unique: boolean
}

export type PropertyValue = ValueProperty | RefProperty

export interface SheetNode {
  name: string
  unique_property: string | null
  properties: PropertyValue[]
  position?: { x: number; y: number }
}

export interface GraphSheetModel {
  project_name: string
  version: number
  created_at: string
  sheets: SheetNode[]
}

export interface Project {
  id: string
  name: string
  model: GraphSheetModel
  last_modified: string
}

export type PropertyConfig =
  | { kind: "value"; name: string; dtype: ScalarType; unique: boolean }
  | { kind: "ref"; name: string; to: string; on: string; edge: string; multi?: MultiSpec; case: CaseMode; on_miss: OnMissMode; unique: boolean }

export interface NodeConfig {
  sheet: string
  unique_property: string | null
  properties: Record<string, PropertyConfig>
}
