import { ArrowRight, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectTrigger, SelectContent, SelectItem } from "@/components/ui/select"
import type React from "react" // Added import for React

interface Sheet {
    name: string
    columns: { name: string; data_type: string }[]
}

interface SheetConnection {
    source_sheet_name: string
    target_sheet_name: string
    edge_name: string
    key: string
}

interface SheetConnectionsProps {
    sheets: Sheet[]
    sheetConnections: SheetConnection[]
    setSheetConnections: React.Dispatch<React.SetStateAction<SheetConnection[]>>
    primaryKey: string
    setPrimaryKey: React.Dispatch<React.SetStateAction<string>>
}

export function SheetConnections({ sheets, sheetConnections, setSheetConnections, primaryKey, setPrimaryKey }: SheetConnectionsProps) {
    const addSheetConnection = () => {
        setSheetConnections([...sheetConnections, { source_sheet_name: "", target_sheet_name: "", edge_name: "", key: "" }])
    }

    const updateSheetConnection = (index: number, field: keyof SheetConnection, value: string) => {
        const updatedConnections = sheetConnections.map((conn, i) => (i === index ? { ...conn, [field]: value } : conn))
        setSheetConnections(updatedConnections)
    }

    const deleteSheetConnection = (index: number) => {
        setSheetConnections(sheetConnections.filter((_, i) => i !== index))
    }

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold">Define Sheet Connections</h3>
            </div>
            <div className="space-y-2">
                <label htmlFor="primaryKey" className="text-sm font-medium">
                    Primary Key Column
                </label>
                <input
                    id="primaryKey"
                    type="text"
                    value={primaryKey}
                    onChange={(e) => setPrimaryKey(e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                    placeholder="Enter primary key column name"
                    required
                />
            </div>
            {sheetConnections.map((conn, index) => (
                <div key={index} className="flex items-center space-x-2 bg-muted p-4 rounded-md">
                    <Select
                        onValueChange={(value) => updateSheetConnection(index, "source_sheet_name", value)}
                        value={conn.source_sheet_name}
                    >
                        <SelectTrigger className="w-1/3">
                            <span>{conn.source_sheet_name || "Select Source"}</span>
                        </SelectTrigger>
                        <SelectContent>
                            {sheets.map((sheet) => (
                                <SelectItem key={sheet.name} value={sheet.name}>
                                    {sheet.name}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <ArrowRight className="w-6 h-6 text-muted-foreground flex-shrink-0" />
                    <Input
                        value={conn.edge_name}
                        onChange={(e) => updateSheetConnection(index, "edge_name", e.target.value)}
                        placeholder="relation_name"
                        className="w-1/3"
                    />
                    <ArrowRight className="w-6 h-6 text-muted-foreground flex-shrink-0" />
                    <Select
                        onValueChange={(value) => updateSheetConnection(index, "target_sheet_name", value)}
                        value={conn.target_sheet_name}
                    >
                        <SelectTrigger className="w-1/3">
                            <span>{conn.target_sheet_name || "Select Target"}</span>
                        </SelectTrigger>
                        <SelectContent>
                            {sheets.map((sheet) => (
                                <SelectItem key={sheet.name} value={sheet.name}>
                                    {sheet.name}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteSheetConnection(index)}
                        className="flex-shrink-0"
                    >
                        <X className="h-4 w-4" />
                        <span className="sr-only">Delete connection</span>
                    </Button>
                </div>
            ))}
            <div className="flex justify-center mt-4">
                <Button type="button" onClick={addSheetConnection} variant="outline">
                    Add new connection
                </Button>
            </div>
        </div>
    )
}

