import { ArrowRight, X, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Select, SelectTrigger, SelectContent, SelectItem } from "@/components/ui/select"
import type React from "react" // Added import for React
import { Sheet, SheetReference } from "@/types/sheets"
import { Card, CardContent } from "@/components/ui/card"

interface ReferencesProps {
    sheets: Sheet[]
    sheetReferences: SheetReference[]
    setSheetReferences: (refs: SheetReference[]) => void
}

export function References({ sheets, sheetReferences, setSheetReferences }: ReferencesProps) {
    const addReference = () => {
        setSheetReferences([
            ...sheetReferences,
            { source_sheet_name: "", source_column_name: "", target_sheet_name: "", target_column_name: "" },
        ])
    }

    const updateReference = (index: number, field: keyof SheetReference, value: string) => {
        const updatedReferences = sheetReferences.map((ref, i) => (i === index ? { ...ref, [field]: value } : ref))
        setSheetReferences(updatedReferences)
    }

    const deleteReference = (index: number) => {
        setSheetReferences(sheetReferences.filter((_, i) => i !== index))
    }

    return (
        <Card className="w-full shadow-none border-0">
            <CardContent className="p-0 space-y-4">
                <div className="flex justify-between items-center w-full">
                    <h3 className="text-lg font-semibold">Define Relations</h3>
                </div>
                {sheetReferences.map((ref, index) => (
                    <div key={index} className="flex flex-col md:flex-row items-center space-y-2 md:space-y-0 md:space-x-2 bg-muted p-4 rounded-md w-full">
                        <Select
                            onValueChange={(value) => updateReference(index, "source_sheet_name", value)}
                            value={ref.source_sheet_name}
                        >
                            <SelectTrigger className="w-full md:w-1/5">
                                <span>{ref.source_sheet_name || "Source Sheet"}</span>
                            </SelectTrigger>
                            <SelectContent>
                                {sheets.map((sheet) => (
                                    <SelectItem key={sheet.name} value={sheet.name}>
                                        {sheet.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <Select
                            onValueChange={(value) => updateReference(index, "source_column_name", value)}
                            value={ref.source_column_name}
                        >
                            <SelectTrigger className="w-full md:w-1/5">
                                <span>{ref.source_column_name || "Source Column"}</span>
                            </SelectTrigger>
                            <SelectContent>
                                {sheets
                                    .find((s) => s.name === ref.source_sheet_name)
                                    ?.columns.map((column) => (
                                        <SelectItem key={column.name} value={column.name}>
                                            {column.name}
                                        </SelectItem>
                                    ))}
                            </SelectContent>
                        </Select>
                        <ArrowRight className="w-6 h-6 text-muted-foreground flex-shrink-0 hidden md:block" />
                        <Select
                            onValueChange={(value) => updateReference(index, "target_sheet_name", value)}
                            value={ref.target_sheet_name}
                        >
                            <SelectTrigger className="w-full md:w-1/5">
                                <span>{ref.target_sheet_name || "Target Sheet"}</span>
                            </SelectTrigger>
                            <SelectContent>
                                {sheets.map((sheet) => (
                                    <SelectItem key={sheet.name} value={sheet.name}>
                                        {sheet.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <Select
                            onValueChange={(value) => updateReference(index, "target_column_name", value)}
                            value={ref.target_column_name}
                        >
                            <SelectTrigger className="w-full md:w-1/5">
                                <span>{ref.target_column_name || "Target Column"}</span>
                            </SelectTrigger>
                            <SelectContent>
                                {sheets
                                    .find((s) => s.name === ref.target_sheet_name)
                                    ?.columns.map((column) => (
                                        <SelectItem key={column.name} value={column.name}>
                                            {column.name}
                                        </SelectItem>
                                    ))}
                            </SelectContent>
                        </Select>
                        <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => deleteReference(index)}
                            className="flex-shrink-0"
                        >
                            <X className="h-4 w-4" />
                            <span className="sr-only">Delete reference</span>
                        </Button>
                    </div>
                ))}
                <div className="flex justify-center mt-4 w-full">
                    <Button
                        type="button"
                        variant="outline"
                        className="w-full"
                        onClick={addReference}
                    >
                        <Plus className="mr-2 h-4 w-4" />
                        Add Reference
                    </Button>
                </div>
            </CardContent>
        </Card>
    )
}