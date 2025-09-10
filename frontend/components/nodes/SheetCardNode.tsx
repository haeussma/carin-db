"use client"

import { memo } from "react"
import { Handle, Position, type NodeProps } from "@xyflow/react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useSchemaStore } from "@/store/useSchemaStore"
import type { NodeConfig } from "@/lib/types"
import { Star, Plus, MoreHorizontal, Trash2 } from "lucide-react"
import { useState } from "react"

interface SheetCardNodeProps extends NodeProps {
  data: {
    nodeName: string
    nodeConfig: NodeConfig
    onPropertyEdit: (nodeId: string, propertyName: string) => void
    isConnecting: boolean
  }
}

export const SheetCardNode = memo(({ data }: SheetCardNodeProps) => {
  const { nodeName, nodeConfig, onPropertyEdit, isConnecting } = data
  const { addProperty, removeProperty, updateProperty, setUniqueProperty, renameSheet, deleteSheet } = useSchemaStore()
  const [newPropName, setNewPropName] = useState("")
  const [editingName, setEditingName] = useState(false)
  const [tempName, setTempName] = useState(nodeName)

  const handleAddProperty = () => {
    if (newPropName.trim()) {
      const newProperty = { kind: "value" as const, name: newPropName.trim(), dtype: "str" as const, unique: false }
      addProperty(nodeName, newProperty)
      setNewPropName("")
    }
  }

  const handleRename = () => {
    if (tempName !== nodeName && tempName.trim()) {
      renameSheet(nodeName, tempName.trim())
    }
    setEditingName(false)
  }

  const handleDelete = () => {
    if (confirm(`Are you sure you want to delete the "${nodeName}" sheet? This cannot be undone.`)) {
      deleteSheet(nodeName)
    }
  }

  const handleUniqueToggle = (propName: string) => {
    const currentProperty = nodeConfig.properties[propName]
    if (currentProperty) {
      const updatedProperty = { ...currentProperty, unique: !currentProperty.unique }
      updateProperty(nodeName, propName, updatedProperty)
    }
  }

  const handlePropertyEdit = (propName: string) => {
    onPropertyEdit(nodeName, propName)
  }

  return (
    <div className="relative w-80" data-connecting={isConnecting}>
      <Card className="w-full shadow-lg overflow-visible relative">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            {editingName ? (
              <Input
                value={tempName}
                onChange={(e) => setTempName(e.target.value)}
                onBlur={handleRename}
                onKeyDown={(e) => e.key === "Enter" && handleRename()}
                className="h-6 text-sm font-medium flex-1 mr-2"
                autoFocus
              />
            ) : (
              <h3
                className="text-sm font-medium cursor-pointer hover:bg-muted px-2 rounded flex-1"
                onClick={() => setEditingName(true)}
              >
                {nodeName}
              </h3>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 hover:bg-red-100 hover:text-red-600"
              onClick={handleDelete}
              title="Delete sheet"
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-2 overflow-visible">
          <div className="max-h-48 overflow-y-auto space-y-1 overflow-x-visible">
            {Object.entries(nodeConfig.properties).map(([propName, prop], index) => {
              const isRef = prop.kind === "ref"

              return (
                <div key={propName} className="flex items-center gap-2 relative py-1" style={{ minHeight: '32px' }}>
                  {/* Clickable star for unique toggle */}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-4 w-4 p-0"
                    onClick={() => handleUniqueToggle(propName)}
                    title={prop.unique ? "Remove unique" : "Set as unique"}
                  >
                    <Star
                      className={`h-3 w-3 ${prop.unique ? 'text-amber-600 fill-amber-600' : 'text-muted-foreground'}`}
                    />
                  </Button>

                  {/* Property name */}
                  <span className="text-xs font-medium truncate flex-1 min-w-0">{propName}</span>

                  {/* Data type or reference info */}
                  <div className="flex items-center gap-1">
                    {isRef ? (
                      <span className="text-xs text-muted-foreground">→ {prop.to}</span>
                    ) : (
                      <span className="text-xs text-muted-foreground">{prop.dtype}</span>
                    )}
                  </div>

                  {/* Edit button */}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-4 w-4 p-0"
                    onClick={() => handlePropertyEdit(propName)}
                    title="Edit property"
                  >
                    <MoreHorizontal className="h-3 w-3 text-muted-foreground" />
                  </Button>
                </div>
              )
            })}
          </div>

          <div className="flex gap-2 pt-2 border-t">
            <Input
              placeholder="Property name"
              value={newPropName}
              onChange={(e) => setNewPropName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddProperty()}
              className="h-7 text-xs"
            />
            <Button variant="outline" size="sm" className="h-7 px-2 bg-transparent" onClick={handleAddProperty}>
              <Plus className="h-3 w-3" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* React Flow Handles - positioned outside card but aligned with property rows */}
      {Object.entries(nodeConfig.properties).map(([propName, prop], index) => {
        // Calculate position: CardHeader (60px) + CardContent padding (8px) + property rows
        const topPosition = 68 + (index * 34) + 16 // 68px for header + padding, 34px per row, 16px to center

        return (
          <div key={`handles-${propName}`}>
            {/* Target handle (left side) */}
            <Handle
              type="target"
              position={Position.Left}
              id={`${propName}-target`}
              style={{
                position: 'absolute',
                left: '-12px',
                top: `${topPosition}px`,
                width: '16px',
                height: '16px',
                backgroundColor: '#3b82f6',
                border: '2px solid white',
                borderRadius: '50%',
                zIndex: 1001
              }}
            />

            {/* Source handle (right side) */}
            <Handle
              type="source"
              position={Position.Right}
              id={`${propName}-source`}
              style={{
                position: 'absolute',
                right: '-12px',
                top: `${topPosition}px`,
                width: '16px',
                height: '16px',
                backgroundColor: 'white',
                border: '2px solid white',
                borderRadius: '50%',
                zIndex: 1001
              }}
            />
          </div>
        )
      })}

    </div>
  )
})

SheetCardNode.displayName = "SheetCardNode"
