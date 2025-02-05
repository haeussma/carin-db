export interface Column {
    name: string
    data_type: string
}

export interface Sheet {
    name: string
    columns: Column[]
}

export interface SheetModel {
    sheets: Sheet[]
}

export interface SheetConnection {
    source_sheet_name: string
    target_sheet_name: string
    edge_name: string
    key: string
}

export interface SheetReference {
    source_sheet_name: string
    source_column_name: string
    target_sheet_name: string
    target_column_name: string
} 