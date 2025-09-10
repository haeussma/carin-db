"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { useSchemaStore } from "@/store/useSchemaStore"
import type { ScalarType, PropertyValue, CaseMode, OnMissMode } from "@/lib/types"
import { ChevronRight, ChevronDown, X, Trash2 } from "lucide-react"

interface PropertyInspectorProps {
    nodeId: string
    propertyName: string
    onClose?: () => void
}

export function PropertyInspector({ nodeId, propertyName, onClose }: PropertyInspectorProps) {
    const { getCurrentModel, updateProperty, removeProperty } = useSchemaStore()
    const [property, setProperty] = useState<PropertyValue | null>(null)
    const [currentPropertyName, setCurrentPropertyName] = useState(propertyName)
    const [advancedOpen, setAdvancedOpen] = useState(false)

    const model = getCurrentModel()

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

        // Safety check: if setting unique to false, check if this property is referenced elsewhere
        if (updates.unique === false && property.unique === true) {
            const isReferenced = checkIfPropertyIsReferenced(nodeId, propertyName)
            if (isReferenced) {
                alert(`Cannot set ${propertyName} as non-unique because it is referenced by other properties. Please remove all references first.`)
                return
            }
        }

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

    const handleTabChange = (tab: string) => {
        if (tab === "value" && property.kind === "ref") {
            handleUpdate({
                kind: "value",
                name: currentPropertyName,
                dtype: "str",
                unique: property.unique
            })
        } else if (tab === "reference" && property.kind === "value") {
            const targetNode = model.sheets[0]?.name || ""
            const targetProp = "id"

            handleUpdate({
                kind: "ref",
                name: currentPropertyName,
                to: targetNode,
                on: targetProp,
                edge: `REFERENCES_${currentPropertyName.toUpperCase()}`,
                case: "insensitive",
                on_miss: "error",
                unique: property.unique,
            })

            // Safety: Ensure the target property is unique
            ensureTargetPropertyIsUnique(targetNode, targetProp)
        }
    }

    const updateRefProperty = (updates: Partial<Omit<PropertyValue & { kind: "ref" }, "kind" | "name">>) => {
        if (property.kind === "ref") {
            handleUpdate({ ...property, ...updates, name: currentPropertyName })
        }
    }

    const getTargetNodeProperties = (): string[] => {
        if (property.kind !== "ref") return []
        const targetNode = model.sheets.find((n) => n.name === property.to)
        return targetNode ? targetNode.properties.map((p) => p.name) : []
    }

    const checkIfPropertyIsReferenced = (nodeId: string, propName: string): boolean => {
        if (!model) return false

        // Check if any other property references this node.property
        for (const sheet of model.sheets) {
            for (const prop of sheet.properties) {
                if (prop.kind === "ref" && prop.to === nodeId && prop.on === propName) {
                    return true
                }
            }
        }
        return false
    }

    const ensureTargetPropertyIsUnique = (targetNodeId: string, targetPropName: string) => {
        if (!model) return

        const targetNode = model.sheets.find((n) => n.name === targetNodeId)
        if (!targetNode) return

        const targetProp = targetNode.properties.find((p) => p.name === targetPropName)
        if (targetProp && !targetProp.unique) {
            // Update the target property to be unique
            const updatedProp = { ...targetProp, unique: true }
            updateProperty(targetNodeId, targetPropName, updatedProp)
        }
    }

    const handleTargetNodeChange = (newTargetNode: string) => {
        const targetNode = model.sheets.find((n) => n.name === newTargetNode)
        const availableProps = targetNode ? targetNode.properties.map((p) => p.name) : []
        const newOn = availableProps.length > 0 ? availableProps[0] : "id"

        updateRefProperty({
            to: newTargetNode,
            on: newOn,
        })

        // Safety: Ensure the target property is unique
        ensureTargetPropertyIsUnique(newTargetNode, newOn)
    }

    const handleDelete = () => {
        removeProperty(nodeId, propertyName)
        onClose?.()
    }

    return (
        <div className="space-y-6 p-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold">Property Inspector</h2>
                    <p className="text-sm text-muted-foreground">
                        {nodeId}.{currentPropertyName}
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
            </div>

            <Separator />

            <Tabs value={property.kind === "ref" ? "reference" : "value"} onValueChange={handleTabChange}>
                <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="value">Value</TabsTrigger>
                    <TabsTrigger value="reference">Reference</TabsTrigger>
                </TabsList>

                <TabsContent value="value" className="space-y-4">
                    <div>
                        <Label className="text-sm">Data Type</Label>
                        <Select
                            value={property.kind === "value" ? property.dtype : "str"}
                            onValueChange={(value) => handleUpdate({ kind: "value", name: currentPropertyName, dtype: value as ScalarType, unique: property.unique })}
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
                </TabsContent>

                <TabsContent value="reference" className="space-y-4">
                    {property.kind === "ref" && (
                        <>
                            <div className="grid grid-cols-2 gap-2">
                                <div>
                                    <Label className="text-sm">Target Node</Label>
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
                                    <Label className="text-sm">Match Property</Label>
                                    <Select value={property.on || ''} onValueChange={(value) => {
                                        updateRefProperty({ on: value })
                                        // Safety: Ensure the target property is unique
                                        ensureTargetPropertyIsUnique(property.to, value)
                                    }}>
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
                                <Label className="text-sm">Edge Label</Label>
                                <Input
                                    value={property.edge || ''}
                                    onChange={(e) => updateRefProperty({ edge: e.target.value.toUpperCase().replace(/\s+/g, "_") })}
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
                                        <Label className="text-sm font-medium">Multiple Values</Label>
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
                                            <Label className="text-sm">Case Sensitivity</Label>
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
                                            <Label className="text-sm">On Missing Value</Label>
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
                        </>
                    )}
                </TabsContent>
            </Tabs>

            <Separator />

            <Button variant="destructive" className="w-full" onClick={handleDelete}>
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Property
            </Button>
        </div>
    )
}
