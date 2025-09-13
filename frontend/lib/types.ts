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
  properties: PropertyValue[]
  position?: { x: number; y: number }
}

export interface GraphSheetModel {
  project_name: string
  created_at: string
  sheets: SheetNode[]
}

export interface Project {
  name: string
  model: GraphSheetModel
  last_modified: string
}