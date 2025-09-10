"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { useSchemaStore } from "@/store/useSchemaStore"
import type { ScalarType, PropertyConfig, PropertyValue, CaseMode, OnMissMode } from "@/lib/types"
import { Trash2, Plus, Star, ChevronRight, ChevronDown, X } from "lucide-react"

interface NodeInspectorProps {
  nodeId: string
  onClose?: () => void
}

function PropertyEditor({
  nodeId,
  propName,
  property,
  isUnique,
  canDelete,
  onDelete,
  onRename,
  onUpdate,
}: {
  nodeId: string
  propName: string
  property: PropertyValue
  isUnique: boolean
  canDelete: boolean
  onDelete: () => void
  onRename: (newName: string) => void
  onUpdate: (newProperty: PropertyValue) => void
}) {
  const { getCurrentModel } = useSchemaStore()
  const model = getCurrentModel()
  const [propertyName, setPropertyName] = useState(propName)
  const [nameError, setNameError] = useState("")
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [isRenaming, setIsRenaming] = useState(false)
  const renameTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (renameTimeoutRef.current) {
        clearTimeout(renameTimeoutRef.current)
      }
    }
  }, [])

  // Update local state when propName changes (after successful rename)
  useEffect(() => {
    setPropertyName(propName)
    setIsRenaming(false)
  }, [propName])

  if (!model) return null

  if (!property) {
    console.log("[v0] PropertyEditor: property config is undefined for", propName)
    return (
      <div className="p-3 border rounded-lg">
        <p className="text-sm text-destructive">Invalid property configuration</p>
      </div>
    )
  }

  const handleNameChange = (newName: string) => {
    setPropertyName(newName)
    setNameError("")

    // Clear any existing timeout
    if (renameTimeoutRef.current) {
      clearTimeout(renameTimeoutRef.current)
    }

    // Check for immediate validation errors
    if (newName !== propName) {
      const node = model.sheets.find((n) => n.name === nodeId)
      if (node && (node.properties || []).some((p) => p.name === newName)) {
        setNameError("Property name already exists")
        return
      }
    }

    // Debounce the actual rename operation
    if (newName.trim() && newName !== propName) {
      setIsRenaming(true)
      renameTimeoutRef.current = setTimeout(() => {
        onRename(newName.trim())
        setIsRenaming(false)
      }, 500) // 500ms delay
    } else {
      setIsRenaming(false)
    }
  }

  const handleTabChange = (tab: string) => {
    if (tab === "value" && property.kind === "ref") {
      onUpdate({ kind: "value", name: propName, dtype: "str", unique: property.unique })
    } else if (tab === "reference" && property.kind === "value") {
      onUpdate({
        kind: "ref",
        name: propName,
        to: model.sheets[0]?.name || "",
        on: "id",
        edge: `REFERENCES_${(propName || 'PROP').toUpperCase()}`,
        case: "insensitive",
        on_miss: "error",
        unique: property.unique,
      })
    }
  }

  const updateRefProperty = (updates: Partial<Omit<PropertyValue & { kind: "ref" }, "kind" | "name">>) => {
    if (property.kind === "ref") {
      onUpdate({ ...property, ...updates, name: propName })
    }
  }

  const formatEdgeLabel = (input: string): string => {
    return input
      .toUpperCase()
      .replace(/\s+/g, "_")
      .replace(/[^A-Z_]/g, "")
  }

  const getTargetNodeProperties = (): string[] => {
    if (property.kind !== "ref") return []
    const targetNode = model.sheets.find((n) => n.name === property.to)
    return targetNode ? (targetNode.properties || []).map((p) => p.name) : []
  }

  const handleTargetNodeChange = (newTargetNode: string) => {
    const targetNode = model.sheets.find((n) => n.name === newTargetNode)
    const availableProps = targetNode ? (targetNode.properties || []).map((p) => p.name) : []
    const newOn = availableProps.length > 0 ? availableProps[0] : "id"

    updateRefProperty({
      to: newTargetNode,
      on: newOn,
    })
  }

  return (
    <div className="p-3 border rounded-lg space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isUnique && <Star className="h-4 w-4 text-amber-600 fill-amber-600" />}
          <div className="space-y-1">
            <Input
              value={propertyName || ''}
              onChange={(e) => handleNameChange(e.target.value)}
              className={`text-sm font-medium h-8 w-32 ${isRenaming ? 'border-blue-300 bg-blue-50' : ''}`}
              placeholder={isRenaming ? "Renaming..." : ""}
            />
            {nameError && <p className="text-xs text-destructive">{nameError}</p>}
          </div>
          <Badge variant={property.kind === "ref" ? "default" : "secondary"} className="text-xs">
            {property.kind === "ref" ? "Reference" : "Value"}
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
          {canDelete && (
            <Button variant="ghost" size="sm" className="text-destructive h-6 w-6 p-0" onClick={onDelete}>
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      <Tabs value={property.kind === "ref" ? "reference" : "value"} onValueChange={handleTabChange}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="value">Value</TabsTrigger>
          <TabsTrigger value="reference">Reference</TabsTrigger>
        </TabsList>

        <TabsContent value="value" className="space-y-3">
          <div>
            <Label className="text-xs">Type</Label>
            <Select
              value={property.kind === "value" ? property.dtype : "str"}
              onValueChange={(value) => onUpdate({ kind: "value", name: propName, dtype: value as ScalarType, unique: property.unique })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="str">String</SelectItem>
                <SelectItem value="int">Integer</SelectItem>
                <SelectItem value="float">Float</SelectItem>
                <SelectItem value="bool">Boolean</SelectItem>
                <SelectItem value="timestamp">Timestamp</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              checked={property.unique}
              onCheckedChange={(checked) => onUpdate({ ...property, unique: checked })}
            />
            <Label className="text-xs">Unique Property</Label>
          </div>
        </TabsContent>

        <TabsContent value="reference" className="space-y-3">
          {property.kind === "ref" && (
            <>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label className="text-xs">Target Node</Label>
                  <Select value={property.to || ''} onValueChange={handleTargetNodeChange}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {model.sheets.map((node) => (
                        <SelectItem key={node.name} value={node.name}>
                          {node.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Match Property</Label>
                  <Select value={property.on || ''} onValueChange={(value) => updateRefProperty({ on: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select property" />
                    </SelectTrigger>
                    <SelectContent>
                      {getTargetNodeProperties().map((propName) => (
                        <SelectItem key={propName} value={propName}>
                          {propName}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <Label className="text-xs">Edge Label</Label>
                <Input
                  value={property.edge || ''}
                  onChange={(e) => updateRefProperty({ edge: formatEdgeLabel(e.target.value) })}
                  placeholder="Edge label"
                />
              </div>

              <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" className="flex items-center gap-2 p-0 h-auto text-sm font-medium">
                    {advancedOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    Advanced Properties
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-3 mt-3">
                  <div className="space-y-3 p-3 bg-muted/50 rounded">
                    <Label className="text-xs font-medium">Multiple Values</Label>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <Label className="text-xs">Separator</Label>
                        <Input
                          value={property.multi?.sep || ","}
                          onChange={(e) =>
                            updateRefProperty({
                              multi: {
                                sep: e.target.value,
                                trim: property.multi?.trim ?? true,
                                allow_empty: property.multi?.allow_empty ?? false,
                              },
                            })
                          }
                          placeholder=","
                        />
                      </div>
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <Switch
                            checked={property.multi?.trim ?? true}
                            onCheckedChange={(checked) =>
                              updateRefProperty({
                                multi: {
                                  sep: property.multi?.sep || ",",
                                  trim: checked,
                                  allow_empty: property.multi?.allow_empty ?? false,
                                },
                              })
                            }
                          />
                          <Label className="text-xs">Trim Values</Label>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <Switch
                            checked={property.multi?.allow_empty ?? false}
                            onCheckedChange={(checked) =>
                              updateRefProperty({
                                multi: {
                                  sep: property.multi?.sep || ",",
                                  trim: property.multi?.trim ?? true,
                                  allow_empty: checked,
                                },
                              })
                            }
                          />
                          <Label className="text-xs">Allow Empty Items</Label>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Label className="text-xs">Case Sensitivity</Label>
                      <Select
                        value={property.case || 'insensitive'}
                        onValueChange={(value) => updateRefProperty({ case: value as CaseMode })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="sensitive">Sensitive</SelectItem>
                          <SelectItem value="insensitive">Insensitive</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs">On Missing Value</Label>
                      <Select
                        value={property.on_miss || 'error'}
                        onValueChange={(value) => updateRefProperty({ on_miss: value as OnMissMode })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="error">Error</SelectItem>
                          <SelectItem value="skip">Skip</SelectItem>
                          <SelectItem value="create">Create</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CollapsibleContent>
              </Collapsible>

              <div className="flex items-center space-x-2">
                <Switch
                  checked={property.unique}
                  onCheckedChange={(checked) => onUpdate({ ...property, unique: checked })}
                />
                <Label className="text-xs">Unique Property</Label>
              </div>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

export function NodeInspector({ nodeId, onClose }: NodeInspectorProps) {
  const { getCurrentModel, renameSheet, addProperty, removeProperty, updateProperty, setUniqueProperty, deleteSheet } =
    useSchemaStore()
  const [newPropName, setNewPropName] = useState("")

  const model = getCurrentModel()
  if (!model) return <div>No project selected</div>

  const node = model.sheets.find((n) => n.name === nodeId)
  if (!node) return <div>Node not found</div>

  const handleNodeNameChange = (newName: string) => {
    if (newName !== nodeId) {
      renameSheet(nodeId, newName)
    }
  }

  const handleUniquePropertyChange = (uniqueProperty: string) => {
    setUniqueProperty(nodeId, uniqueProperty === "none" ? null : uniqueProperty)
  }

  const handleAddProperty = () => {
    if (newPropName.trim()) {
      const newProperty: PropertyValue = { kind: "value", name: newPropName.trim(), dtype: "str", unique: false }
      addProperty(nodeId, newProperty)
      setNewPropName("")
    }
  }

  const handlePropertyUpdate = (propName: string, newProperty: PropertyValue) => {
    // Ensure the name field is preserved
    const propertyWithName = { ...newProperty, name: propName }
    updateProperty(nodeId, propName, propertyWithName)
  }

  const handlePropertyRename = (oldName: string, newName: string) => {
    const property = (node.properties || []).find((p) => p.name === oldName)
    if (property) {
      // Update the property with the new name, keeping the old name for the updateProperty call
      updateProperty(nodeId, oldName, { ...property, name: newName })
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Node Inspector</h2>
          <p className="text-sm text-muted-foreground">Configure {nodeId}</p>
        </div>
        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="node-name">Node Name</Label>
          <Input
            id="node-name"
            value={nodeId}
            onChange={(e) => handleNodeNameChange(e.target.value)}
            placeholder="Enter node name"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="unique-prop">Unique Property</Label>
          <Select value={node.unique_property || "none"} onValueChange={handleUniquePropertyChange}>
            <SelectTrigger>
              <SelectValue placeholder="Select unique property" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">None</SelectItem>
              {(node.properties || []).map((prop) => (
                <SelectItem key={`${nodeId}-${prop.name}`} value={prop.name}>
                  {prop.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Separator />

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Properties</h3>
          <span className="text-xs text-muted-foreground">{(node.properties || []).length} properties</span>
        </div>

        <ScrollArea className="h-96">
          <div className="space-y-4">
            {(node.properties || []).map((prop) => {
              const isUnique = prop.name === node.unique_property
              const canDelete = prop.name !== node.unique_property

              return (
                <PropertyEditor
                  key={`${nodeId}-${prop.name}`}
                  nodeId={nodeId}
                  propName={prop.name}
                  property={prop}
                  isUnique={isUnique}
                  canDelete={canDelete}
                  onDelete={() => removeProperty(nodeId, prop.name)}
                  onRename={(newName) => handlePropertyRename(prop.name, newName)}
                  onUpdate={(newProperty) => handlePropertyUpdate(prop.name, newProperty)}
                />
              )
            })}
          </div>
        </ScrollArea>

        <div className="flex gap-2">
          <Input
            placeholder="Property name"
            value={newPropName || ''}
            onChange={(e) => setNewPropName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddProperty()}
          />
          <Button variant="outline" onClick={handleAddProperty}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Separator />

      <Button variant="destructive" className="w-full" onClick={() => deleteSheet(nodeId)}>
        Delete Node
      </Button>
    </div>
  )
}
