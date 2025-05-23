"use client"

import { useState, useCallback, useEffect } from "react"
import { useDropzone } from "react-dropzone"
import { Upload, File, Link2, Globe } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { StatusMessage } from "@/components/StatusMessage"
import { SheetConnections } from "@/components/SheetConnections"
import { References } from "@/components/References"
import InteractiveGraphVisualization from "@/components/InteractiveGraphVisualization"
import {
  SheetModel,
  SheetConnection,
  SheetReferences,
  validate
} from "@/components/appconfig"

const CONNECTION_ERROR = "Connection to server failed. Please check that the backend server is running at http://localhost:8000 and try again."

interface SheetReference {
  source_sheet_name: string;
  source_column_name: string;
  target_sheet_name: string;
  target_column_name: string;
}

// Helper function to convert SheetReferences to SheetReference
const convertToSheetReference = (ref: SheetReferences): SheetReference => ({
  source_sheet_name: ref.source_sheet_name || "",
  source_column_name: ref.source_column_name || "",
  target_sheet_name: ref.target_sheet_name || "",
  target_column_name: ref.target_column_name || ""
});

// Helper function to convert SheetReference to SheetReferences
const convertToSheetReferences = (ref: SheetReference): SheetReferences => ({
  source_sheet_name: ref.source_sheet_name,
  source_column_name: ref.source_column_name,
  target_sheet_name: ref.target_sheet_name,
  target_column_name: ref.target_column_name
});

export default function SpreadsheetUploader() {
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [filePath, setFilePath] = useState<string>("")
  const [sheetModel, setSheetModel] = useState<SheetModel>({ sheets: [], sheet_connections: [], sheet_references: [] })
  const [sheetConnections, setSheetConnections] = useState<SheetConnection[]>([])
  const [sheetReferences, setSheetReferences] = useState<SheetReferences[]>([])
  const [displayReferences, setDisplayReferences] = useState<SheetReference[]>([])
  const [primaryKey, setPrimaryKey] = useState<string>("")
  const [statusMessage, setStatusMessage] = useState("")
  const [statusColor, setStatusColor] = useState("")
  const [activeTab, setActiveTab] = useState("connections")
  const [hasSubmitted, setHasSubmitted] = useState(false)
  const [isLoadingModel, setIsLoadingModel] = useState(false)

  // Update displayReferences when sheetReferences changes
  useEffect(() => {
    setDisplayReferences(sheetReferences.map(convertToSheetReference));
  }, [sheetReferences]);

  // Function to handle references updates from the References component
  const handleReferencesUpdate = (newReferences: SheetReference[]) => {
    setDisplayReferences(newReferences);
    setSheetReferences(newReferences.map(convertToSheetReferences));
  };

  // Function to load graph model from backend
  const loadGraphModel = useCallback(async () => {
    setIsLoadingModel(true);
    try {
      const response = await fetch("/api/config/sheet_model");

      // If we get a 404 or other error, it's fine for first-time uploads
      // Just log it and continue with empty model
      if (!response.ok) {
        console.log("No existing graph model found, starting fresh");
        setIsLoadingModel(false);
        return;
      }

      const data = await response.json();
      console.log("Loaded graph model:", data);

      // If we have data, update the state
      if (data && Object.keys(data).length > 0) {
        try {
          // Set sheet connections if available
          if (data.sheet_connections && Array.isArray(data.sheet_connections) && data.sheet_connections.length > 0) {
            // Extract primary key from the first connection's key field
            const firstConnection = data.sheet_connections[0];
            if (firstConnection && firstConnection.key) {
              const primaryKeyValue = String(firstConnection.key);
              console.log("Setting primary key from connection:", primaryKeyValue);
              setPrimaryKey(primaryKeyValue);
            }

            setSheetConnections(data.sheet_connections);
          }

          // Set sheet references if available
          if (data.sheet_references && Array.isArray(data.sheet_references)) {
            setSheetReferences(data.sheet_references);
          }
        } catch (parseError) {
          console.error("Error parsing model data:", parseError);
        }
      }
    } catch (error) {
      // Handle network errors (like server not running)
      console.error("Error loading graph model:", error);
      // Don't show error to user, just log it - this is fine for first-time use
    } finally {
      setIsLoadingModel(false);
    }
  }, []);

  // Load graph model when component mounts
  useEffect(() => {
    loadGraphModel();
  }, [loadGraphModel]);

  // Function to check if all sheet connections are completely filled out
  const areConnectionsValid = () => {
    if (sheetConnections.length === 0) {
      return sheetReferences.length > 0; // Valid if we have references instead
    }

    // Check if all connections have all fields filled out
    return sheetConnections.every(conn =>
      conn.source_sheet_name &&
      conn.target_sheet_name &&
      conn.edge_name &&
      conn.key
    );
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const droppedFile = acceptedFiles[0]
    setFile(droppedFile)
    setIsUploading(true)
    setStatusMessage("")
    setStatusColor("")

    const formData = new FormData()
    formData.append("file", droppedFile)

    try {
      const uploadRes = await fetch("/api/spreadsheet/upload", {
        method: "POST",
        body: formData,
      })

      if (!uploadRes.ok) {
        const errorData = await uploadRes.json()
        throw new Error(errorData.detail?.message || "Upload failed")
      }

      const file_path = await uploadRes.text();
      console.log("File path is here:", file_path);

      const validateRes = await fetch(
        `/api/spreadsheet/validate_spreadsheet?path=${encodeURIComponent(file_path)}`,
        { method: "POST" }
      );

      const data = await validateRes.json();
      console.log("Data is here:", data);

      if (!validateRes.ok) {
        if (validateRes.status === 400 && data.type_inconsistencies) {
          const errorMessages = data.type_inconsistencies.map((inc: any) =>
            `Sheet "${inc.sheet_name}", Column "${inc.column}": Found mixed data types ${inc.data_types.join(', ')} in rows ${inc.rows.join(', ')}`
          );
          setStatusMessage(`Data type inconsistencies found:\n${errorMessages.join('\n')}`);
          setStatusColor("red");
          throw new Error("Data type inconsistencies found in spreadsheet");
        }
        throw new Error(data.detail?.message || "Validation failed");
      }

      // Check if we have sheets data
      if (!data.sheets || !Array.isArray(data.sheets)) {
        throw new Error("Invalid response: missing sheets data");
      }

      const validatedModel: SheetModel = {
        sheets: data.sheets,
        sheet_connections: sheetConnections,
        sheet_references: sheetReferences
      };

      setSheetModel(validatedModel);
      setFilePath(file_path);

    } catch (error: any) {
      console.error("Error processing spreadsheet:", error);
      setStatusMessage(error.message || "Failed to process spreadsheet");
      setStatusColor("red");
    } finally {
      setIsUploading(false);
    }
  }, [sheetConnections, sheetReferences]);

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
    e.preventDefault();
    if (!file || !filePath || !areConnectionsValid()) return;

    setIsUploading(true);
    setStatusMessage("");
    setStatusColor("");
    setHasSubmitted(true);

    try {
      const connectionsWithKey = primaryKey
        ? sheetConnections.map(conn => ({
          ...conn,
          key: conn.key || primaryKey
        }))
        : sheetConnections;

      const graphModelData: SheetModel = {
        sheets: sheetModel.sheets,
        sheet_connections: connectionsWithKey,
        sheet_references: sheetReferences,
      };

      // First save the sheet model
      const saveModelRes = await fetch("/api/config/sheet_model", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(graphModelData),
      });

      if (!saveModelRes.ok) {
        const errorData = await saveModelRes.json();
        throw new Error(errorData.detail?.message || "Failed to save sheet model");
      }

      // Then process the spreadsheet
      // log the file path about to be sent
      console.log("File path about to be sent:", filePath);

      const processRes = await fetch("/api/spreadsheet/process", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(filePath)
      });

      if (!processRes.ok) {
        const errorData = await processRes.json();
        if (processRes.status === 404) {
          throw new Error("File not found. Please try uploading the file again.");
        } else if (processRes.status === 400) {
          throw new Error(errorData.detail?.message || "Invalid request. Please check your input.");
        } else {
          throw new Error(errorData.detail?.message || "Failed to process spreadsheet");
        }
      }

      const result = await processRes.json();
      setStatusMessage(result.message || "Data successfully added to the knowledgebase!");
      setStatusColor("green");

      // Reset form on success
      setFile(null);
      setFilePath("");
      setSheetModel({ sheets: [], sheet_connections: [], sheet_references: [] });
      setSheetConnections([]);
      setSheetReferences([]);
      setPrimaryKey("");

    } catch (error: any) {
      console.error("Error processing data:", error);
      setStatusMessage(error.message || "An unexpected error occurred");
      setStatusColor("red");
    } finally {
      setIsUploading(false);
    }
  };

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
            </div>

            {/* Connect Data Card - Only show if we have sheet model data */}
            {sheetModel.sheets.length > 0 && (
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
                            sheetReferences={displayReferences}
                            setSheetReferences={handleReferencesUpdate}
                          />
                        </TabsContent>
                      </Tabs>
                    </div>

                    {/* Right side - Graph Visualization */}
                    <div className="w-full h-full min-h-[500px] flex items-center justify-center border-2 border-gray-300 rounded-md overflow-hidden bg-white">
                      <div className="w-full h-full">
                        <InteractiveGraphVisualization
                          sheetModel={sheetModel}
                          sheetConnections={sheetConnections}
                          sheetReferences={displayReferences}
                        />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </CardContent>

          <CardFooter className="px-0 w-full mt-4">
            <Button
              type="submit"
              className="w-full"
              disabled={!file || isUploading || !areConnectionsValid() || !filePath}
            >
              {isUploading ? "Processing..." : "Add to knowledgebase"}
            </Button>
          </CardFooter>
        </form>
        {(hasSubmitted || statusMessage) && (
          <StatusMessage
            message={statusMessage}
            type={statusColor === "green" ? "success" : statusColor === "red" ? "error" : "info"}
          />
        )}
      </Card>
    </div>
  )
}


