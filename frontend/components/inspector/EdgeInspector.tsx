"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronDown, ArrowRight, X } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { useSchemaStore } from "@/store/useSchemaStore"
import type { RefProperty } from "@/lib/types"

export type CaseMode = "sensitive" | "insensitive"
export type OnMissMode = "error" | "skip" | "create"

export interface MultiSpec {
  sep: string
  trim: boolean
  allow_empty: boolean
}

interface EdgeInspectorProps {
  edgeId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function EdgeInspector({ edgeId, open, onOpenChange }: EdgeInspectorProps) {
  const { getCurrentProject, updateEdge, deleteEdge } = useSchemaStore()
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false)

  const project = getCurrentProject()
  const model = project.model

  // Parse edge ID to get source and target info
  const [sourceSheet, sourceProp, targetSheet, targetProp] = edgeId.split('.')

  // Find the actual edge property in the model
  const sourceSheetNode = model.sheets.find(s => s.name === sourceSheet)
  const targetSheetNode = model.sheets.find(s => s.name === targetSheet)
  const edgeProperty = sourceSheetNode?.properties.find(p => p.name === sourceProp && p.kind === 'ref') as RefProperty | undefined

  // Get available nodes and properties
  const availableNodes = model.sheets.map(s => s.name)
  const sourceProperties = sourceSheetNode?.properties.map(p => p.name) || []
  const targetProperties = targetSheetNode?.properties.map(p => p.name) || []

  // Initialize local state from edge property
  const [config, setConfig] = useState({
    sourceNode: sourceSheet,
    sourceProperty: sourceProp,
    targetNode: targetSheet,
    targetProperty: targetProp,
    edgeName: edgeProperty?.edge || '',
    case: (edgeProperty?.case || 'sensitive') as CaseMode,
    on_miss: (edgeProperty?.on_miss || 'error') as OnMissMode,
    unique: edgeProperty?.unique || false,
    multi: edgeProperty?.multi || { sep: ',', trim: true, allow_empty: false }
  })

  // Update local state when edge changes
  useEffect(() => {
    if (edgeProperty) {
      setConfig({
        sourceNode: sourceSheet,
        sourceProperty: sourceProp,
        targetNode: edgeProperty.to,
        targetProperty: edgeProperty.on,
        edgeName: edgeProperty.edge,
        case: edgeProperty.case || 'sensitive',
        on_miss: edgeProperty.on_miss || 'error',
        unique: edgeProperty.unique || false,
        multi: edgeProperty.multi || { sep: ',', trim: true, allow_empty: false }
      })
    }
  }, [edgeId, edgeProperty, sourceSheet, sourceProp])

  const handleEdgeNameChange = (value: string) => {
    // Convert to uppercase and replace spaces with underscores
    const formatted = value
      .toUpperCase()
      .replace(/\s+/g, "_")
      .replace(/[^A-Z_]/g, "")
    setConfig((prev) => ({ ...prev, edgeName: formatted }))
  }

  // Save changes to state when dialog closes
  const handleDialogClose = (open: boolean) => {
    if (!open && edgeProperty) {
      // Dialog is closing, save any changes
      const updatedProperty: RefProperty = {
        ...edgeProperty,
        to: config.targetNode,
        on: config.targetProperty,
        edge: config.edgeName,
        case: config.case,
        on_miss: config.on_miss,
        unique: config.unique,
        multi: config.multi
      }

      // Only update if something actually changed
      if (
        edgeProperty.to !== config.targetNode ||
        edgeProperty.on !== config.targetProperty ||
        edgeProperty.edge !== config.edgeName ||
        edgeProperty.case !== config.case ||
        edgeProperty.on_miss !== config.on_miss ||
        edgeProperty.unique !== config.unique ||
        JSON.stringify(edgeProperty.multi) !== JSON.stringify(config.multi)
      ) {
        updateEdge(edgeId, updatedProperty)
      }
    }
    onOpenChange(open)
  }

  const handleDelete = () => {
    if (confirm(`Delete this relationship? This cannot be undone.`)) {
      deleteEdge(edgeId)
      onOpenChange(false)
    }
  }

  if (!edgeProperty || !sourceSheetNode || !targetSheetNode) {
    return (
      <Dialog open={open} onOpenChange={handleDialogClose}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edge Not Found</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Could not find edge data for: {edgeId}
          </p>
          <Button onClick={() => onOpenChange(false)}>Close</Button>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onOpenChange={handleDialogClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl font-bold text-foreground">Edit Relationship</DialogTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleDialogClose(false)}
              className="h-6 w-6 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="space-y-6">
          <div className="flex items-center gap-4 p-4 bg-muted/30 rounded-lg border border-border">
            {/* Source Node - Read Only */}
            <div className="flex-1 space-y-2">
              <Label className="text-xs text-muted-foreground">Source Node</Label>
              <div className="px-3 py-2 bg-muted rounded-md border border-border text-sm">
                {config.sourceNode}
              </div>
            </div>

            {/* Source Property - Read Only */}
            <div className="flex-1 space-y-2">
              <Label className="text-xs text-muted-foreground">Source Property</Label>
              <div className="px-3 py-2 bg-muted rounded-md border border-border text-sm">
                {config.sourceProperty}
              </div>
            </div>

            {/* Arrow with Edge Name Input */}
            <div className="flex flex-col items-center gap-2 px-4">
              <Input
                value={config.edgeName}
                onChange={(e) => handleEdgeNameChange(e.target.value)}
                placeholder="EDGE_NAME"
                className="w-32 text-center font-mono text-sm bg-accent/20 border-accent"
              />
              <ArrowRight className="w-6 h-6 text-accent" />
            </div>

            {/* Target Node - Read Only */}
            <div className="flex-1 space-y-2">
              <Label className="text-xs text-muted-foreground">Target Node</Label>
              <div className="px-3 py-2 bg-muted rounded-md border border-border text-sm">
                {config.targetNode}
              </div>
            </div>

            {/* Target Property - Read Only */}
            <div className="flex-1 space-y-2">
              <Label className="text-xs text-muted-foreground">Target Property</Label>
              <div className="px-3 py-2 bg-muted rounded-md border border-border text-sm">
                {config.targetProperty}
              </div>
            </div>
          </div>

          {/* Advanced Options */}
          <Collapsible open={isAdvancedOpen} onOpenChange={setIsAdvancedOpen}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="w-full justify-between p-0 h-auto">
                <span className="text-sm font-medium">Advanced Options</span>
                <ChevronDown className={`w-4 h-4 transition-transform ${isAdvancedOpen ? "rotate-180" : ""}`} />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-4 mt-4 p-4 bg-muted/30 rounded-lg border border-border">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="case" className="text-sm font-medium">
                    Case Sensitivity
                  </Label>
                  <Select
                    value={config.case}
                    onValueChange={(value: CaseMode) => setConfig((prev) => ({ ...prev, case: value }))}
                  >
                    <SelectTrigger className="border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sensitive">Case Sensitive</SelectItem>
                      <SelectItem value="insensitive">Case Insensitive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="onMiss" className="text-sm font-medium">
                    On Missing Target
                  </Label>
                  <Select
                    value={config.on_miss}
                    onValueChange={(value: OnMissMode) => setConfig((prev) => ({ ...prev, on_miss: value }))}
                  >
                    <SelectTrigger className="border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="error">Throw Error</SelectItem>
                      <SelectItem value="skip">Skip Connection</SelectItem>
                      <SelectItem value="create">Create Target</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="unique"
                  checked={config.unique}
                  onCheckedChange={(checked) => setConfig((prev) => ({ ...prev, unique: checked }))}
                />
                <Label htmlFor="unique" className="text-sm font-medium">
                  Unique Relationship
                </Label>
              </div>

              {/* Multi Spec Configuration */}
              <div className="space-y-3 p-3 bg-background rounded border border-border">
                <Label className="text-sm font-medium">Multi-Value Configuration</Label>
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="separator" className="text-xs">
                      Separator
                    </Label>
                    <Input
                      id="separator"
                      value={config.multi.sep}
                      onChange={(e) =>
                        setConfig((prev) => ({
                          ...prev,
                          multi: { ...prev.multi, sep: e.target.value },
                        }))
                      }
                      placeholder=","
                      className="text-xs"
                    />
                  </div>
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="trim"
                      checked={config.multi.trim}
                      onCheckedChange={(checked) =>
                        setConfig((prev) => ({
                          ...prev,
                          multi: { ...prev.multi, trim: checked },
                        }))
                      }
                    />
                    <Label htmlFor="trim" className="text-xs">
                      Trim Whitespace
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="allowEmpty"
                      checked={config.multi.allow_empty}
                      onCheckedChange={(checked) =>
                        setConfig((prev) => ({
                          ...prev,
                          multi: { ...prev.multi, allow_empty: checked },
                        }))
                      }
                    />
                    <Label htmlFor="allowEmpty" className="text-xs">
                      Allow Empty
                    </Label>
                  </div>
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>

          {/* Delete Button */}
          <div className="flex justify-start pt-4 border-t border-border">
            <Button
              variant="destructive"
              onClick={handleDelete}
            >
              Delete Relationship
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}