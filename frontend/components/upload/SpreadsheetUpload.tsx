"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useSchemaStore } from "@/store/useSchemaStore"
import { useToast } from "@/hooks/use-toast"
import { Upload, FileSpreadsheet } from "lucide-react"
import * as XLSX from "xlsx"

interface SpreadsheetUploadProps {
  onClose: () => void
}

interface SheetData {
  name: string
  columns: string[]
  nodeName: string
  uniqueProperty: string
}

export function SpreadsheetUpload({ onClose }: SpreadsheetUploadProps) {
  const { loadFromSpreadsheet } = useSchemaStore()
  const { toast } = useToast()
  const [sheets, setSheets] = useState<SheetData[]>([])
  const [loading, setLoading] = useState(false)

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setLoading(true)
    try {
      const arrayBuffer = await file.arrayBuffer()
      const workbook = XLSX.read(arrayBuffer, { type: "array" })

      const sheetData: SheetData[] = workbook.SheetNames.map((sheetName) => {
        const worksheet = workbook.Sheets[sheetName]
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as string[][]
        const columns = jsonData[0] || []

        return {
          name: sheetName,
          columns: columns.filter((col) => col && col.trim()),
          nodeName: sheetName,
          uniqueProperty: columns[0] || "id",
        }
      })

      setSheets(sheetData)
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to parse spreadsheet file",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const updateSheet = (index: number, updates: Partial<SheetData>) => {
    setSheets((prev) => prev.map((sheet, i) => (i === index ? { ...sheet, ...updates } : sheet)))
  }

  const handleImport = () => {
    const sheetsMap: Record<string, string[]> = {}

    sheets.forEach((sheet) => {
      if (sheet.nodeName.trim()) {
        sheetsMap[sheet.nodeName.trim()] = sheet.columns
      }
    })

    loadFromSpreadsheet(sheetsMap)

    // Update unique properties
    sheets.forEach((sheet) => {
      if (sheet.nodeName.trim() && sheet.uniqueProperty) {
        useSchemaStore.getState().setUniqueProperty(sheet.nodeName.trim(), sheet.uniqueProperty)
      }
    })

    toast({
      title: "Success",
      description: `Imported ${sheets.length} sheets as nodes`,
    })

    onClose()
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Import Spreadsheet</h3>
        </div>

        <div className="space-y-2">
          <Label htmlFor="file">Select Excel file (.xlsx)</Label>
          <Input id="file" type="file" accept=".xlsx,.xls" onChange={handleFileUpload} disabled={loading} />
        </div>
      </div>

      {sheets.length > 0 && (
        <div className="space-y-4">
          <h4 className="text-sm font-medium">Configure Sheets</h4>

          <ScrollArea className="h-96">
            <div className="space-y-4">
              {sheets.map((sheet, index) => (
                <Card key={sheet.name}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm">Sheet: {sheet.name}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="space-y-2">
                      <Label htmlFor={`node-name-${index}`}>Node Name</Label>
                      <Input
                        id={`node-name-${index}`}
                        value={sheet.nodeName}
                        onChange={(e) => updateSheet(index, { nodeName: e.target.value })}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor={`unique-prop-${index}`}>Unique Property</Label>
                      <Select
                        value={sheet.uniqueProperty}
                        onValueChange={(value) => updateSheet(index, { uniqueProperty: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {sheet.columns.map((column) => (
                            <SelectItem key={column} value={column}>
                              {column}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs text-muted-foreground">Columns ({sheet.columns.length})</Label>
                      <div className="flex flex-wrap gap-1">
                        {sheet.columns.map((column) => (
                          <span key={column} className="text-xs bg-muted px-2 py-1 rounded">
                            {column}
                          </span>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={handleImport}>
              <Upload className="h-4 w-4 mr-2" />
              Import Sheets
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
