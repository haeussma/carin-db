import { ArrowRight, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectTrigger, SelectContent, SelectItem } from "@/components/ui/select"
import type React from "react"
import { Card, CardDescription, CardHeader, CardTitle, CardContent } from "./ui/card"
import { useEffect, useMemo } from "react"

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

export function SheetConnections({
    sheets,
    sheetConnections,
    setSheetConnections,
    primaryKey,
    setPrimaryKey,
}: SheetConnectionsProps) {
    const addSheetConnection = () => {
        setSheetConnections([
            ...sheetConnections,
            { source_sheet_name: "", target_sheet_name: "", edge_name: "", key: primaryKey },
        ])
    }

    const updateSheetConnection = (index: number, field: keyof SheetConnection, value: string) => {
        const updated = sheetConnections.map((conn, i) => (i === index ? { ...conn, [field]: value } : conn))
        setSheetConnections(updated)
    }

    // Debug
    useEffect(() => {
        console.log("SheetConnections received primaryKey:", primaryKey)
    }, [primaryKey])

    // Keep each connection's key synced with global primaryKey
    useEffect(() => {
        if (primaryKey && sheetConnections.length > 0) {
            const updated = sheetConnections.map((c) => ({ ...c, key: primaryKey }))
            setSheetConnections(updated)
        }
    }, [primaryKey, setSheetConnections]) // sheetConnections is read from render; no need in deps

    // 1) Only sheets that contain the primaryKey column (case-insensitive)
    const sheetsWithPK = useMemo(() => {
        const pk = primaryKey?.trim().toLowerCase()
        if (!pk) return sheets
        return sheets.filter((s) => s.columns?.some((c) => c.name?.trim().toLowerCase() === pk))
    }, [sheets, primaryKey])

    // 3) Clear selections that no longer qualify when PK changes
    useEffect(() => {
        const valid = new Set(sheetsWithPK.map((s) => s.name))
        let changed = false
        const fixed = sheetConnections.map((conn) => {
            let src = conn.source_sheet_name
            let tgt = conn.target_sheet_name
            if (src && !valid.has(src)) {
                src = ""
                changed = true
            }
            if (tgt && !valid.has(tgt)) {
                tgt = ""
                changed = true
            }
            return { ...conn, source_sheet_name: src, target_sheet_name: tgt }
        })
        if (changed) setSheetConnections(fixed)
    }, [sheetsWithPK, sheetConnections, setSheetConnections])

    const deleteSheetConnection = (index: number) => {
        setSheetConnections(sheetConnections.filter((_, i) => i !== index))
    }

    const noEligible = sheetsWithPK.length === 0
    const notEnoughToConnect = sheetsWithPK.length < 2

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
                        {/* Source */}
                        <Select
                            onValueChange={(value) => updateSheetConnection(index, "source_sheet_name", value)}
                            value={conn.source_sheet_name}
                            disabled={noEligible}
                        >
                            <SelectTrigger className="w-full md:w-1/3">
                                <span>{conn.source_sheet_name || "Select Source"}</span>
                            </SelectTrigger>
                            <SelectContent>
                                {noEligible ? (
                                    <SelectItem value="__none__" disabled>
                                        No sheets with “{primaryKey}”
                                    </SelectItem>
                                ) : (
                                    sheetsWithPK.map((sheet) => (
                                        <SelectItem key={sheet.name} value={sheet.name}>
                                            {sheet.name}
                                        </SelectItem>
                                    ))
                                )}
                            </SelectContent>
                        </Select>

                        <ArrowRight className="w-6 h-6 text-muted-foreground flex-shrink-0 hidden md:block" />

                        {/* Edge name */}
                        <Input
                            value={conn.edge_name}
                            onChange={(e) => updateSheetConnection(index, "edge_name", e.target.value)}
                            placeholder="relation_name"
                            className="w-full md:w-1/3"
                        />

                        <ArrowRight className="w-6 h-6 text-muted-foreground flex-shrink-0 hidden md:block" />

                        {/* Target */}
                        <Select
                            onValueChange={(value) => updateSheetConnection(index, "target_sheet_name", value)}
                            value={conn.target_sheet_name}
                            disabled={noEligible}
                        >
                            <SelectTrigger className="w-full md:w-1/3">
                                <span>{conn.target_sheet_name || "Select Target"}</span>
                            </SelectTrigger>
                            <SelectContent>
                                {noEligible ? (
                                    <SelectItem value="__none__" disabled>
                                        No sheets with “{primaryKey}”
                                    </SelectItem>
                                ) : (
                                    sheetsWithPK.map((sheet) => (
                                        <SelectItem key={sheet.name} value={sheet.name}>
                                            {sheet.name}
                                        </SelectItem>
                                    ))
                                )}
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
                    <Button
                        type="button"
                        onClick={addSheetConnection}
                        variant="outline"
                        className="w-full"
                        disabled={notEnoughToConnect}
                        title={notEnoughToConnect ? "Need at least two sheets containing the primary key" : undefined}
                    >
                        Add new connection
                    </Button>
                </div>
            </CardContent>
        </Card>
    )
}
