"use client"

import { useState, useCallback, useEffect } from "react"
import { useDropzone } from "react-dropzone"
import { Upload, File } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { StatusMessage } from "@/components/status-message"
import { SheetConnections } from "@/components/SheetConnections"
import { References } from "@/components/References"
import InteractiveGraphVisualization from "@/components/InteractiveGraphVisualization"

interface Column {
  name: string
  data_type: string
}

interface Sheet {
  name: string
  columns: Column[]
}

interface SheetModel {
  sheets: Sheet[]
}

interface SheetConnection {
  source_sheet_name: string
  target_sheet_name: string
  edge_name: string
  key: string
}

interface SheetReference {
  source_sheet_name: string
  source_column_name: string
  target_sheet_name: string
  target_column_name: string
}

export default function SpreadsheetUploader() {
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [sheetModel, setSheetModel] = useState<SheetModel>({ sheets: [] })
  const [sheetConnections, setSheetConnections] = useState<SheetConnection[]>([])
  const [sheetReferences, setSheetReferences] = useState<SheetReference[]>([])
  const [primaryKey, setPrimaryKey] = useState<string>("")
  const [statusMessage, setStatusMessage] = useState("")
  const [statusColor, setStatusColor] = useState("")

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const droppedFile = acceptedFiles[0]
    setFile(droppedFile)

    const formData = new FormData()
    formData.append("file", droppedFile)

    try {
      const response = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Upload failed")
      }

      // log the response so that it appears in docker console
      console.log(response)

      const data = await response.json()
      setSheetModel(data.data)
      setStatusMessage("Spreadsheet data successfully added!")
      setStatusColor("green")
    } catch (error: any) {
      console.error("Error adding spreadsheet:", error)
      setStatusMessage(`Failed to upload spreadsheet: ${error.message}`)
      setStatusColor("red")
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "text/csv": [".csv"],
    },
    multiple: false,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !primaryKey) return

    setIsUploading(true)

    // Update all sheet connections to use the primary key
    const connectionsWithKey = sheetConnections.map(conn => ({
      ...conn,
      key: primaryKey
    }))

    const formData = new FormData()
    formData.append("file", file)
    formData.append(
      "data",
      JSON.stringify({
        sheet_connections: connectionsWithKey,
        sheet_references: sheetReferences,
      }),
    )

    // Log the data being sent for debugging
    console.log("Sending data:", {
      primaryKey,
      connections: connectionsWithKey,
      references: sheetReferences
    })

    try {
      const response = await fetch("http://localhost:8000/api/process_file", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Upload failed")
      }

      setStatusMessage("Spreadsheet, relationships, and references uploaded successfully!")
      setStatusColor("green")
      setFile(null)
      setSheetConnections([])
      setSheetReferences([])
      setPrimaryKey("")
    } catch (error: any) {
      console.error("Error adding spreadsheet:", error)
      setStatusMessage(`Failed to add spreadsheet data: ${error.message}`)
      setStatusColor("red")
    } finally {
      setIsUploading(false)
    }
  }

  useEffect(() => {
    if (statusMessage) {
      const timer = setTimeout(() => {
        setStatusMessage("")
        setStatusColor("")
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [statusMessage])

  return (
    <div className="space-y-8">
      <Card className={`w-full max-w-4xl mx-auto p-8 ${statusColor ? `border-${statusColor}-500` : ""} transition-colors duration-300`}>
        <CardHeader>
          <CardTitle className="text-2xl font-bold text-center">Add Data</CardTitle>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-6">
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-md p-4 text-center cursor-pointer transition-colors ${isDragActive ? "border-primary bg-primary/10" : "border-gray-300 hover:border-primary"}`}
            >
              <input {...getInputProps()} />
              {file ? (
                <div className="flex items-center justify-center space-x-2">
                  <File className="w-6 h-6 text-primary" />
                  <span className="font-medium">{file.name}</span>
                </div>
              ) : (
                <div>
                  <Upload className="w-8 h-8 mx-auto text-gray-400" />
                  <p className="mt-2">Drag &amp; drop a spreadsheet (.xlsx) here, or click to select one</p>
                </div>
              )}
            </div>

            <SheetConnections
              sheets={sheetModel.sheets}
              sheetConnections={sheetConnections}
              setSheetConnections={setSheetConnections}
              primaryKey={primaryKey}
              setPrimaryKey={setPrimaryKey}
            />
            <References sheets={sheetModel.sheets} sheetReferences={sheetReferences} setSheetReferences={setSheetReferences} />
          </CardContent>
          <CardFooter>
            <Button
              type="submit"
              className="w-full"
              disabled={!file || !primaryKey || isUploading}
            >
              {isUploading ? "Uploading..." : "Add to knowledgebase"}
            </Button>
          </CardFooter>
        </form>
        <StatusMessage message={statusMessage} />
      </Card>

      {/* Interactive Graph Visualization */}
      {sheetModel.sheets.length > 0 && (
        <InteractiveGraphVisualization
          sheetModel={sheetModel}
          sheetConnections={sheetConnections}
          sheetReferences={sheetReferences}
        />
      )}
    </div>
  )
}

