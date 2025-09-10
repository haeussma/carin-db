"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useSchemaStore } from "@/store/useSchemaStore"
import { useToast } from "@/hooks/use-toast"
import { Upload, Download, Save, Play, FileJson } from "lucide-react"
import { SpreadsheetUpload } from "@/components/upload/SpreadsheetUpload"
import { ProjectSelector } from "@/components/layout/ProjectSelector"

export function TopBar() {
  const { getCurrentModel, exportJson, importJson } = useSchemaStore()
  const { toast } = useToast()
  const [backendUrl, setBackendUrl] = useState(() =>
    typeof window !== "undefined"
      ? localStorage.getItem("backendUrl") || "http://localhost:8000"
      : "http://localhost:8000",
  )
  const [uploadOpen, setUploadOpen] = useState(false)

  const model = getCurrentModel()

  const handleBackendUrlChange = (url: string) => {
    setBackendUrl(url)
    localStorage.setItem("backendUrl", url)
  }

  const handleSaveToBackend = async () => {
    if (!model) {
      toast({
        title: "Error",
        description: "No project selected",
        variant: "destructive",
      })
      return
    }

    try {
      const response = await fetch(`${backendUrl}/api/config/sheet_model`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(model),
      })

      if (response.ok) {
        toast({ title: "Success", description: "Configuration saved to backend" })
      } else {
        throw new Error(`HTTP ${response.status}`)
      }
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to save to backend: ${error}`,
        variant: "destructive",
      })
    }
  }

  const handleImportJson = () => {
    const input = document.createElement("input")
    input.type = "file"
    input.accept = ".json"
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (file) {
        const reader = new FileReader()
        reader.onload = (e) => {
          try {
            const json = JSON.parse(e.target?.result as string)
            importJson(json)
            toast({ title: "Success", description: "JSON imported successfully" })
          } catch (error) {
            toast({
              title: "Error",
              description: "Invalid JSON file",
              variant: "destructive",
            })
          }
        }
        reader.readAsText(file)
      }
    }
    input.click()
  }

  const handleExportJson = () => {
    const json = exportJson()
    const blob = new Blob([json], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "graph_sheet_model.json"
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleProcessSpreadsheet = async () => {
    const filePath = prompt("Enter spreadsheet file path (e.g., uploads/data.xlsx):")
    if (!filePath) return

    try {
      const response = await fetch(`${backendUrl}/api/spreadsheet/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: filePath }),
      })

      if (response.ok) {
        const result = await response.json()
        toast({ title: "Success", description: "Spreadsheet processed successfully" })
      } else {
        throw new Error(`HTTP ${response.status}`)
      }
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to process spreadsheet: ${error}`,
        variant: "destructive",
      })
    }
  }

  return (
    <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-4 gap-4">
        <ProjectSelector />

        <div className="flex items-center gap-2 ml-auto">
          <Input
            placeholder="Backend URL"
            value={backendUrl}
            onChange={(e) => handleBackendUrlChange(e.target.value)}
            className="w-48"
          />

          <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <Upload className="h-4 w-4 mr-2" />
                Upload Spreadsheet
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Upload Spreadsheet</DialogTitle>
              </DialogHeader>
              <SpreadsheetUpload onClose={() => setUploadOpen(false)} />
            </DialogContent>
          </Dialog>

          <Button variant="outline" size="sm" onClick={handleImportJson}>
            <FileJson className="h-4 w-4 mr-2" />
            Import JSON
          </Button>

          <Button variant="outline" size="sm" onClick={handleExportJson}>
            <Download className="h-4 w-4 mr-2" />
            Export JSON
          </Button>

          <Button variant="outline" size="sm" onClick={handleSaveToBackend}>
            <Save className="h-4 w-4 mr-2" />
            Save to Backend
          </Button>

          <Button variant="outline" size="sm" onClick={handleProcessSpreadsheet}>
            <Play className="h-4 w-4 mr-2" />
            Process Spreadsheet
          </Button>
        </div>
      </div>
    </div>
  )
}
