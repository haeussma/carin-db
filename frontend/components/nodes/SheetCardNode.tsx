"use client"

import { memo, useState } from "react"
import { Handle, Position, type NodeProps } from "@xyflow/react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useSchemaStore } from "@/store/useSchemaStore"
import type { SheetNode, PropertyValue, RefProperty } from "@/lib/types"
import { Star, Plus, MoreHorizontal, Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"

type SheetCardNodeProps = NodeProps & {
  data: {
    nodeName: string
    sheetNode: SheetNode
    onPropertyEdit: (nodeId: string, propertyName: string) => void
    isConnecting: boolean
  }
}

const isRef = (p: PropertyValue): p is RefProperty => p.kind === "ref"

export const SheetCardNode = memo(({ data }: SheetCardNodeProps) => {
  const { sheetNode, onPropertyEdit, isConnecting } = data
  const nodeName = sheetNode.name
  const { addProperty, updateProperty, renameSheet, deleteSheet } = useSchemaStore()

  const [newPropName, setNewPropName] = useState("")
  const [editingName, setEditingName] = useState(false)
  const [tempName, setTempName] = useState(nodeName)
  const [editingProperty, setEditingProperty] = useState<string | null>(null)
  const [tempPropertyName, setTempPropertyName] = useState("")

  // Note: No need to update node internals since handles are always rendered

  // --- actions -------------------------------------------------------------

  const handleAddProperty = () => {
    const name = newPropName.trim()
    if (!name) return
    addProperty(nodeName, { kind: "value", name, dtype: "str", unique: false })
    setNewPropName("")
  }

  const handleRename = () => {
    const name = tempName.trim()
    if (name && name !== nodeName) renameSheet(nodeName, name)
    setEditingName(false)
  }

  const handleDelete = () => {
    if (confirm(`Delete sheet "${nodeName}"? This cannot be undone.`)) {
      deleteSheet(nodeName)
    }
  }

  const handleUniqueToggle = (propName: string) => {
    const current = sheetNode.properties.find(p => p.name === propName)
    if (!current) return
    updateProperty(nodeName, propName, { ...current, unique: !current.unique })
  }

  const handlePropertyEdit = (propName: string) => {
    onPropertyEdit(nodeName, propName)
  }

  const startRenameProperty = (propName: string) => {
    setEditingProperty(propName)
    setTempPropertyName(propName)
  }

  const commitRenameProperty = (oldName: string) => {
    const newName = tempPropertyName.trim()
    if (!newName || newName === oldName) {
      setEditingProperty(null)
      setTempPropertyName("")
      return
    }
    const current = sheetNode.properties.find(p => p.name === oldName)
    if (!current) return
    updateProperty(nodeName, oldName, { ...current, name: newName })
    setEditingProperty(null)
    setTempPropertyName("")
  }

  // --- render --------------------------------------------------------------

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
                className="h-8 text-lg font-medium flex-1 mr-2"
                autoFocus
              />
            ) : (
              <h3
                className="text-lg font-medium cursor-pointer hover:bg-muted px-2 py-1 rounded flex-1"
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

        <CardContent className="space-y-1 overflow-visible rounded-md p-0">
          <div className="flex flex-col w-full overflow-y-auto overflow-x-visible rounded-md overflow-visible">
            {sheetNode.properties.map((prop, index) => {
              const propName = prop.name
              const ref = isRef(prop)

              return (
                <div
                  key={`${propName}-${index}`}
                  className="flex items-center gap-2 rounded-md overflow-visible p-2"
                  style={{ minHeight: 32 }}
                >
                  {/* Always render target handle, but hide when not connecting */}
                  <Handle
                    type="target"
                    position={Position.Left}
                    id={`${nodeName}-${prop.name}-target`}
                    className={cn("!size-4 !relative !transform-none", !isConnecting && '!opacity-0 !pointer-events-none')}
                    style={{ backgroundColor: 'hsl(var(--accent))', border: '2px solid hsl(var(--accent-foreground))' }}
                  />
                  {/* Unique toggle */}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-4 w-4 p-0"
                    onClick={() => handleUniqueToggle(propName)}
                    title={prop.unique ? "Remove unique" : "Set as unique"}
                  >
                    <Star className={`h-3 w-3 ${prop.unique ? "text-amber-600 fill-amber-600" : "text-muted-foreground"}`} />
                  </Button>

                  {/* Editable property name */}
                  {editingProperty === propName ? (
                    <Input
                      value={tempPropertyName}
                      onChange={(e) => setTempPropertyName(e.target.value)}
                      onBlur={() => commitRenameProperty(propName)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") commitRenameProperty(propName)
                        if (e.key === "Escape") {
                          setEditingProperty(null)
                          setTempPropertyName("")
                        }
                      }}
                      className="h-5 text-xs font-medium flex-1 min-w-0 px-1"
                      autoFocus
                    />
                  ) : (
                    <span
                      className="text-xs font-medium truncate flex-1 min-w-0 cursor-pointer hover:bg-muted px-1 rounded"
                      onClick={() => startRenameProperty(propName)}
                    >
                      {propName}
                    </span>
                  )}

                  {/* Type / ref info */}
                  <div className="flex items-center gap-1">
                    {ref ? (
                      <span className="text-xs text-muted-foreground">→ {prop.to}</span>
                    ) : (
                      <span className="text-xs text-muted-foreground">{prop.dtype}</span>
                    )}
                  </div>

                  {/* Open inspector */}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-4 w-4 p-0"
                    onClick={() => handlePropertyEdit(propName)}
                    title="Edit property"
                  >
                    <MoreHorizontal className="h-3 w-3 text-muted-foreground" />
                  </Button>
                  <Handle
                    type="source"
                    position={Position.Right}
                    id={`${nodeName}-${prop.name}-source`}
                    className="!size-4 !relative !transform-none !z-[1001]"
                    style={{ backgroundColor: 'hsl(var(--accent))', border: '2px solid hsl(var(--accent-foreground))' }}
                  />
                </div>
              )
            })}
          </div>

          {/* add property */}
          <div className="flex gap-2 pt-4 border-t p-6">
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
    </div>
  )
})

SheetCardNode.displayName = "SheetCardNode"
