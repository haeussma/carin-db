"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { useSchemaStore } from "@/store/useSchemaStore"
import type { ScalarType, PropertyValue } from "@/lib/types"
import { X, Trash2 } from "lucide-react"

interface PropertyInspectorProps {
    nodeId: string
    propertyName: string
    onClose?: () => void
}

export function PropertyInspector({ nodeId, propertyName, onClose }: PropertyInspectorProps) {
    const { getCurrentProject, updateProperty, removeProperty } = useSchemaStore()
    const [property, setProperty] = useState<PropertyValue | null>(null)
    const [currentPropertyName, setCurrentPropertyName] = useState(propertyName)

    const project = getCurrentProject()
    const model = project?.model

    useEffect(() => {
        if (model) {
            const node = model.sheets.find((n) => n.name === nodeId)
            const prop = node?.properties.find((p) => p.name === propertyName)
            if (prop) {
                setProperty(prop)
                setCurrentPropertyName(prop.name)
            }
        }
    }, [model, nodeId, propertyName])

    if (!model || !property) {
        return (
            <div className="space-y-6 p-6">
                <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Property Inspector</h2>
                    {onClose && (
                        <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
                            <X className="h-4 w-4" />
                        </Button>
                    )}
                </div>
                <div>Property not found</div>
            </div>
        )
    }

    const handleUpdate = (updates: Partial<PropertyValue>) => {
        if (!property) return

        const updatedProperty = { ...property, ...updates } as PropertyValue
        setProperty(updatedProperty)
        updateProperty(nodeId, propertyName, updatedProperty)
    }

    const handleNameChange = (newName: string) => {
        setCurrentPropertyName(newName)
        if (newName.trim() && newName !== propertyName) {
            handleUpdate({ name: newName.trim() })
        }
    }

    const handleDelete = () => {
        removeProperty(nodeId, propertyName)
        onClose?.()
    }

    return (
        <div className="space-y-6 p-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold">{nodeId} {currentPropertyName}</h2>
                </div>
                {onClose && (
                    <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
                        <X className="h-4 w-4" />
                    </Button>
                )}
            </div>

            <div className="space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="property-name">Property Name</Label>
                    <Input
                        id="property-name"
                        value={currentPropertyName}
                        onChange={(e) => handleNameChange(e.target.value)}
                        placeholder="Enter property name"
                    />
                </div>

                <div className="flex items-center space-x-2">
                    <Switch
                        checked={property.unique}
                        onCheckedChange={(checked) => handleUpdate({ unique: checked })}
                    />
                    <Label className="text-sm">Unique Property</Label>
                </div>

                {property.kind === "value" && (
                    <div className="space-y-2">
                        <Label className="text-sm">Data Type</Label>
                        <Select
                            value={property.dtype}
                            onValueChange={(value) => handleUpdate({ dtype: value as ScalarType })}
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
                )}
            </div>

            <div className="flex justify-start pt-4 border-t border-border">
                <Button variant="destructive" onClick={handleDelete}>
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete Property
                </Button>
            </div>
        </div>
    )
}
