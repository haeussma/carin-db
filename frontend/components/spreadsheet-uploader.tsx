"use client"

import { useState, useCallback, useEffect } from "react"
import { useDropzone } from "react-dropzone"
import { Upload, File, Link2, GitBranch, Globe } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { StatusMessage } from "@/components/StatusMessage"
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
  const [activeTab, setActiveTab] = useState("connections")
  const [hasSubmitted, setHasSubmitted] = useState(false)
  const [isLoadingModel, setIsLoadingModel] = useState(false)

  // Function to load graph model from backend
  const loadGraphModel = useCallback(async () => {
    setIsLoadingModel(true);
    try {
      const response = await fetch("http://localhost:8000/api/load_graph_model");

      if (!response.ok) {
        throw new Error("Failed to load graph model");
      }

      const data = await response.json();
      console.log("Loaded graph model:", data);

      // If we have data, update the state
      if (data && Object.keys(data).length > 0) {
        // Set sheet connections if available
        if (data.sheet_connections && Array.isArray(data.sheet_connections) && data.sheet_connections.length > 0) {
          // Extract primary key from the first connection's key field
          const firstConnection = data.sheet_connections[0];
          if (firstConnection && firstConnection.key) {
            const primaryKeyValue = String(firstConnection.key);
            console.log("Setting primary key from connection:", primaryKeyValue);
            setPrimaryKey(primaryKeyValue);
          }

          setSheetConnections(data.sheet_connections.map((conn: any) => ({
            source_sheet_name: conn.source_sheet_name || "",
            target_sheet_name: conn.target_sheet_name || "",
            edge_name: conn.edge_name || "",
            key: conn.key || ""
          })));
        } else if (data.primary_key !== undefined) {
          // Fallback to primary_key field if available
          const primaryKeyValue = String(data.primary_key);
          console.log("Setting primary key from primary_key field:", primaryKeyValue);
          setPrimaryKey(primaryKeyValue);
        }

        // Set sheet references if available
        if (data.sheet_references && Array.isArray(data.sheet_references)) {
          setSheetReferences(data.sheet_references.map((ref: any) => ({
            source_sheet_name: ref.source_sheet_name || "",
            source_column_name: ref.source_column_name || "",
            target_sheet_name: ref.target_sheet_name || "",
            target_column_name: ref.target_column_name || ""
          })));
        }
      }
    } catch (error) {
      console.error("Error loading graph model:", error);
      // Don't show error to user, just log it
    } finally {
      setIsLoadingModel(false);
    }
  }, []);

  // Load graph model when component mounts
  useEffect(() => {
    loadGraphModel();
  }, [loadGraphModel]);

  // Debug primary key changes
  useEffect(() => {
    console.log("Primary key changed to:", primaryKey);
  }, [primaryKey]);

  // Function to check if all sheet connections are completely filled out
  const areConnectionsValid = () => {
    if (sheetConnections.length === 0) {
      return sheetReferences.length > 0; // Valid if we have references instead
    }

    // Check if all connections have all fields filled out
    return sheetConnections.every(conn =>
      conn.source_sheet_name &&
      conn.target_sheet_name &&
      conn.edge_name
    );
  };

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

      const data = await response.json()
      setSheetModel(data.data)

      // After loading sheet model, try to load graph model to prefill connections
      loadGraphModel();

      setStatusMessage("Spreadsheet data successfully loaded!")
      setStatusColor("green")
    } catch (error: any) {
      console.error("Error adding spreadsheet:", error)

      // Handle network errors specifically
      if (error.message === "Failed to fetch") {
        setStatusMessage(
          "Connection to server failed. Please check that the backend server is running at http://localhost:8000 and try again."
        )
      } else {
        setStatusMessage(`Failed to upload spreadsheet: ${error.message}`)
      }
      setStatusColor("red")
    }
  }, [loadGraphModel])

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
    if (!file) return  // Only check for file, not primaryKey

    setIsUploading(true)
    setStatusMessage("")
    setStatusColor("")
    setHasSubmitted(true)

    try {
      // Update all sheet connections to use the primary key
      const connectionsWithKey = sheetConnections.map(conn => ({
        ...conn,
        key: primaryKey
      }))

      // Prepare the graph model data - don't include primary_key as a separate field
      const graphModelData = {
        sheet_connections: connectionsWithKey,
        sheet_references: sheetReferences,
      };

      console.log("Saving graph model data:", graphModelData);

      // First, upload the file to get the sheet model
      const formData = new FormData()
      formData.append("file", file)
      formData.append("data", JSON.stringify({
        ...graphModelData,
        primary_key: primaryKey || "", // Include primary_key for the backend process_file endpoint
      }))

      try {
        const response = await fetch("http://localhost:8000/api/process_file", {
          method: "POST",
          body: formData,
        })

        const result = await response.json()

        if (!response.ok) {
          // Format and display the error message
          let errorMessage = "Error processing file"

          if (result.detail) {
            errorMessage = result.detail

            // Format validation errors for better readability
            if (errorMessage.includes("Missing Values:") ||
              errorMessage.includes("Missing Sheets:") ||
              errorMessage.includes("Missing Columns:")) {
              errorMessage = errorMessage.replace(/\n/g, "<br/>")
            }
          }

          setStatusMessage(errorMessage)
          setStatusColor("red")
          throw new Error(errorMessage)
        }

        // Save the graph model for future use
        try {
          const saveModelResponse = await fetch("http://localhost:8000/api/save_graph_model", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(graphModelData),
          });

          if (!saveModelResponse.ok) {
            console.error("Failed to save graph model for future use");
          }
        } catch (saveError) {
          console.error("Error saving graph model:", saveError);
          // Don't fail the whole process if saving the model fails
        }

        // Success
        setStatusMessage("Data successfully added to the knowledgebase!")
        setStatusColor("green")

        // Reset form
        setFile(null)
        setSheetModel({ sheets: [] })
        setSheetConnections([])
        setSheetReferences([])
        setPrimaryKey("")
      } catch (fetchError: any) {
        console.error("Fetch error:", fetchError)

        // Handle network errors specifically
        if (fetchError.message === "Failed to fetch") {
          setStatusMessage(
            "Connection to server failed. Please check that the backend server is running at http://localhost:8000 and try again."
          )
        } else {
          setStatusMessage(fetchError.message || "An unexpected error occurred")
        }
        setStatusColor("red")
      }
    } catch (error: any) {
      console.error("Error processing data:", error)
      if (!statusMessage) {
        setStatusMessage(error.message || "An unexpected error occurred")
        setStatusColor("red")
      }
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="w-full">
      <Card className="w-full mx-auto p-4">
        <CardHeader>
          <CardTitle className="text-2xl font-bold text-center">Add Data</CardTitle>
        </CardHeader>

        <form onSubmit={handleSubmit} className="w-full">
          <CardContent className="space-y-6 p-0 w-full">
            {/* Upload section - moved above the grid */}
            <div
              {...getRootProps()}
              className={`w-full border-2 border-dashed rounded-md p-6 text-center cursor-pointer transition-colors ${isDragActive ? "border-primary bg-primary/10" : "border-gray-300 hover:border-primary"}`}
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
              {isLoadingModel && (
                <div className="mt-2 text-xs text-blue-600">
                  Loading saved connections...
                </div>
              )}
            </div>

            {/* Connect Data Card */}
            <Card className="w-full shadow-none border-0">
              <CardHeader className="px-0 pt-6 pb-2">
                <CardTitle className="text-lg font-semibold">Connect Data</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {/* Two-column grid for connections/references and visualization */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
                  {/* Left side - Connections and References tabs */}
                  <div className="w-full">
                    {/* Tabbed interface for Connections and References */}
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                      <TabsList className="grid grid-cols-2 mb-4 w-full">
                        <TabsTrigger value="connections" className="flex items-center gap-2">
                          <Globe className="h-4 w-4" />
                          <span>Connect multiple sheets</span>
                        </TabsTrigger>
                        <TabsTrigger value="references" className="flex items-center gap-2">
                          <Link2 className="h-4 w-4" />
                          <span>Connect pairs of sheets</span>
                        </TabsTrigger>
                      </TabsList>

                      <TabsContent value="connections" className="mt-0 w-full">
                        <SheetConnections
                          sheets={sheetModel.sheets}
                          sheetConnections={sheetConnections}
                          setSheetConnections={setSheetConnections}
                          primaryKey={primaryKey}
                          setPrimaryKey={setPrimaryKey}
                        />
                      </TabsContent>

                      <TabsContent value="references" className="mt-0 w-full">
                        <References
                          sheets={sheetModel.sheets}
                          sheetReferences={sheetReferences}
                          setSheetReferences={setSheetReferences}
                        />
                      </TabsContent>
                    </Tabs>
                  </div>

                  {/* Right side - Graph Visualization */}
                  <div className="w-full h-full min-h-[500px] flex items-center justify-center border-2 border-gray-300 rounded-md overflow-hidden bg-white">
                    {sheetModel.sheets.length > 0 ? (
                      <div className="w-full h-full">
                        <InteractiveGraphVisualization
                          sheetModel={sheetModel}
                          sheetConnections={sheetConnections}
                          sheetReferences={sheetReferences}
                        />
                      </div>
                    ) : (
                      <div className="text-center text-gray-500">
                        <p>Upload a spreadsheet to visualize its structure</p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </CardContent>

          <CardFooter className="px-0 w-full">
            <Button
              type="submit"
              className="w-full"
              disabled={!file || isUploading || !areConnectionsValid()}
            >
              {isUploading ? "Uploading..." : "Add to knowledgebase"}
            </Button>
          </CardFooter>
        </form>
        {hasSubmitted && (
          <StatusMessage
            message={statusMessage}
            type={statusColor === "green" ? "success" : statusColor === "red" ? "error" : "info"}
          />
        )}
      </Card>
    </div>
  )
}

