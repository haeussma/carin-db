import { ArrowRight, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectTrigger, SelectContent, SelectItem } from "@/components/ui/select"
import type React from "react" // Added import for React
import { Card, CardDescription, CardHeader, CardTitle, CardContent } from "./ui/card"
import { useEffect } from "react"

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
        setSheetConnections([...sheetConnections, { source_sheet_name: "", target_sheet_name: "", edge_name: "", key: primaryKey }])
    }

    const updateSheetConnection = (index: number, field: keyof SheetConnection, value: string) => {
        const updatedConnections = sheetConnections.map((conn, i) => (i === index ? { ...conn, [field]: value } : conn))
        setSheetConnections(updatedConnections)
    }

    // Debug primary key changes
    useEffect(() => {
        console.log("SheetConnections received primaryKey:", primaryKey);
    }, [primaryKey]);

    // Update all connections when primary key changes
    useEffect(() => {
        if (primaryKey && sheetConnections.length > 0) {
            const updatedConnections = sheetConnections.map(conn => ({
                ...conn,
                key: primaryKey
            }))
            setSheetConnections(updatedConnections)
        }
    }, [primaryKey])

    const deleteSheetConnection = (index: number) => {
        setSheetConnections(sheetConnections.filter((_, i) => i !== index))
    }

    return (
        <Card className="w-full shadow-none border-0">
            <CardHeader>
                <CardTitle className="text-left">Connect Data</CardTitle>
                <CardDescription className="text-left">
                    Choose a column name that is common to multiple sheets by which data will be joined
                </CardDescription>
            </CardHeader>
            <CardContent className="p-0 space-y-4">
                <div className="space-y-2 w-full">
                    <label htmlFor="primaryKey" className="text-sm font-medium">
                        Primary Key Column
                    </label>
                    <input
                        id="primaryKey"
                        type="text"
                        value={primaryKey || ""}
                        onChange={(e) => setPrimaryKey(e.target.value)}
                        className="w-full px-3 py-2 border rounded-md"
                        placeholder="Enter primary key column name"
                        required
                    />
                </div>
                {sheetConnections.map((conn, index) => (
                    <div key={index} className="flex items-center space-x-2 bg-muted p-4 rounded-md w-full">
                        <Select
                            onValueChange={(value) => updateSheetConnection(index, "source_sheet_name", value)}
                            value={conn.source_sheet_name}
                        >
                            <SelectTrigger className="w-full md:w-1/3">
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
                        <ArrowRight className="w-6 h-6 text-muted-foreground flex-shrink-0 hidden md:block" />
                        <Input
                            value={conn.edge_name}
                            onChange={(e) => updateSheetConnection(index, "edge_name", e.target.value)}
                            placeholder="relation_name"
                            className="w-full md:w-1/3"
                        />
                        <ArrowRight className="w-6 h-6 text-muted-foreground flex-shrink-0 hidden md:block" />
                        <Select
                            onValueChange={(value) => updateSheetConnection(index, "target_sheet_name", value)}
                            value={conn.target_sheet_name}
                        >
                            <SelectTrigger className="w-full md:w-1/3">
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
                <div className="flex justify-center mt-4 w-full">
                    <Button type="button" onClick={addSheetConnection} variant="outline" className="w-full">
                        Add new connection
                    </Button>
                </div>
            </CardContent>
        </Card>
    )
}

