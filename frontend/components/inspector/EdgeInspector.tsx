"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { useSchemaStore } from "@/store/useSchemaStore"
import type { CaseMode, OnMissMode } from "@/lib/types"
import { X } from "lucide-react"

interface EdgeInspectorProps {
  edgeId: string
  onClose?: () => void
}

export function EdgeInspector({ edgeId, onClose }: EdgeInspectorProps) {
  const { getCurrentModel, updateEdge, deleteEdge } = useSchemaStore()
  const model = getCurrentModel()

  if (!model) {
    return <div>No model available</div>
  }

  const [sourceNode, sourceProp] = edgeId.split(".")
  const node = model.sheets.find((n) => n.name === sourceNode)
  const property = (node?.properties || []).find(p => p.name === sourceProp)

  if (!node || !property || property.kind !== "ref") {
    return <div>Edge not found</div>
  }

  const refProp = property
  const targetNode = model.sheets.find((n) => n.name === refProp.to)

  const handleUpdate = (patch: Partial<typeof refProp>) => {
    updateEdge(edgeId, patch)
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Edge Inspector</h2>
          <p className="text-sm text-muted-foreground">
            {sourceNode}.{sourceProp} → {refProp.to}
          </p>
        </div>
        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="target">Target Node</Label>
          <Select value={refProp.to} onValueChange={(to) => handleUpdate({ to })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {model.sheets.map((nodeConfig) => (
                <SelectItem key={nodeConfig.name} value={nodeConfig.name}>
                  {nodeConfig.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="on">Target Property</Label>
          <Select
            value={refProp.on}
            onValueChange={(on) => handleUpdate({ on })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {targetNode &&
                (targetNode.properties || []).map((prop) => (
                  <SelectItem key={`${sourceNode}-${prop.name}`} value={prop.name}>
                    {prop.name}
                    {prop.name === targetNode.unique_property && " ⭐"}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="edge">Edge Type</Label>
          <Input id="edge" value={refProp.edge} onChange={(e) => handleUpdate({ edge: e.target.value })} />
        </div>
      </div>

      <Separator />

      <div className="space-y-4">
        <h3 className="text-sm font-medium">Multi-Value Settings</h3>

        <div className="space-y-2">
          <Label htmlFor="separator">Separator</Label>
          <Input
            id="separator"
            value={refProp.multi?.sep || ","}
            onChange={(e) =>
              handleUpdate({
                multi: {
                  ...refProp.multi,
                  sep: e.target.value,
                  trim: refProp.multi?.trim ?? true,
                  allow_empty: refProp.multi?.allow_empty ?? false,
                },
              })
            }
          />
        </div>

        <div className="flex items-center justify-between">
          <Label htmlFor="trim">Trim Whitespace</Label>
          <Switch
            id="trim"
            checked={refProp.multi?.trim ?? true}
            onCheckedChange={(trim) =>
              handleUpdate({
                multi: {
                  ...refProp.multi,
                  trim,
                  sep: refProp.multi?.sep || ",",
                  allow_empty: refProp.multi?.allow_empty ?? false,
                },
              })
            }
          />
        </div>

        <div className="flex items-center justify-between">
          <Label htmlFor="allow-empty">Allow Empty Values</Label>
          <Switch
            id="allow-empty"
            checked={refProp.multi?.allow_empty ?? false}
            onCheckedChange={(allow_empty) =>
              handleUpdate({
                multi: {
                  ...refProp.multi,
                  allow_empty,
                  sep: refProp.multi?.sep || ",",
                  trim: refProp.multi?.trim ?? true,
                },
              })
            }
          />
        </div>
      </div>

      <Separator />

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="case">Case Sensitivity</Label>
          <Select
            value={refProp.case || "insensitive"}
            onValueChange={(case_mode) => handleUpdate({ case: case_mode as CaseMode })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="insensitive">Case Insensitive</SelectItem>
              <SelectItem value="sensitive">Case Sensitive</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="on-miss">On Missing</Label>
          <Select
            value={refProp.on_miss || "error"}
            onValueChange={(on_miss) => handleUpdate({ on_miss: on_miss as OnMissMode })}
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

      <Separator />

      <Button variant="destructive" className="w-full" onClick={() => deleteEdge(edgeId)}>
        Delete Edge
      </Button>
    </div>
  )
}
