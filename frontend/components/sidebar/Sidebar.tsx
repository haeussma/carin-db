"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { useSchemaStore } from "@/store/useSchemaStore"
import { Plus, Search, Settings, Trash2 } from "lucide-react"

export function Sidebar() {
  const { model, addNode, deleteNode, selectNode, issues } = useSchemaStore()
  const [searchTerm, setSearchTerm] = useState("")
  const [newNodeName, setNewNodeName] = useState("")

  const filteredNodes = model.nodes.filter((node) => node.sheet.toLowerCase().includes(searchTerm.toLowerCase()))

  const handleAddNode = () => {
    if (newNodeName.trim()) {
      addNode(newNodeName.trim())
      setNewNodeName("")
    } else {
      addNode()
    }
  }

  const getNodeIssueCount = (nodeName: string) => {
    return issues.filter((issue) => issue.node === nodeName).length
  }

  return (
    <div className="h-full border-r bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="p-4 space-y-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search nodes..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-8"
            />
          </div>

          <div className="flex gap-2">
            <Input
              placeholder="Node name"
              value={newNodeName}
              onChange={(e) => setNewNodeName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddNode()}
              className="h-8"
            />
            <Button variant="outline" size="sm" onClick={handleAddNode}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <Separator />

        <ScrollArea className="h-64">
          <div className="space-y-1">
            {filteredNodes.map((nodeConfig) => {
              const nodeName = nodeConfig.sheet
              const issueCount = getNodeIssueCount(nodeName)

              return (
                <div
                  key={nodeName}
                  className="flex items-center justify-between p-2 rounded-md hover:bg-muted cursor-pointer group"
                  onClick={() => selectNode(nodeName)}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="text-sm font-medium truncate">{nodeName}</span>
                    {issueCount > 0 && (
                      <Badge variant="destructive" className="h-4 text-xs">
                        {issueCount}
                      </Badge>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 text-destructive"
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteNode(nodeName)
                    }}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              )
            })}
          </div>
        </ScrollArea>

        <Separator />

        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            <span className="text-sm font-medium">Global Settings</span>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="version" className="text-xs">
                Version
              </Label>
              <Input
                id="version"
                type="number"
                value={model.version}
                onChange={(e) => {
                  const version = Number.parseInt(e.target.value) || 1
                  useSchemaStore.setState((state) => ({
                    model: { ...state.model, version },
                  }))
                }}
                className="h-6 w-16 text-xs"
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="enforce-ref" className="text-xs">
                Enforce Ref on Unique
              </Label>
              <Switch
                id="enforce-ref"
                checked={model.enforce_ref_on_unique}
                onCheckedChange={(checked) => {
                  useSchemaStore.setState((state) => ({
                    model: { ...state.model, enforce_ref_on_unique: checked },
                  }))
                  useSchemaStore.getState().recomputeIssues()
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
