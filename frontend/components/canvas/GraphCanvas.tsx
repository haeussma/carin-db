"use client"

import type React from "react"
import { useCallback, useEffect, useRef, useState } from "react"
import { useSchemaStore } from "@/store/useSchemaStore"
import { Star, Info, Trash2, Plus } from "lucide-react"
import type { JSX } from "react/jsx-runtime"

interface Position {
  x: number
  y: number
}

interface CanvasNode {
  id: string
  position: Position
  width: number
  height: number
}

interface GraphCanvasProps {
  onSelectionChange?: (nodePosition: { x: number; y: number }, nodeWidth: number) => void
}

export function GraphCanvas({ onSelectionChange }: GraphCanvasProps) {
  const { getCurrentModel, selectNode, selectEdge, clearSelection, createOrUpdateRef, deleteSheet, addSheet } =
    useSchemaStore()

  const canvasRef = useRef<HTMLDivElement>(null)
  const [nodes, setNodes] = useState<Record<string, CanvasNode>>({})
  const [dragState, setDragState] = useState<{
    isDragging: boolean
    nodeId?: string
    offset?: Position
    isConnecting?: boolean
    sourceNode?: string
    sourceProp?: string
    connectionLine?: { start: Position; current: Position }
  }>({ isDragging: false })

  const model = getCurrentModel()

  useEffect(() => {
    if (!model) return

    const nodeEntries = model.sheets.map((s) => s.name)
    const newNodes: Record<string, CanvasNode> = {}

    nodeEntries.forEach((nodeId, index) => {
      if (!nodes[nodeId]) {
        newNodes[nodeId] = {
          id: nodeId,
          position: {
            x: 50 + (index % 3) * 320,
            y: 50 + Math.floor(index / 3) * 220,
          },
          width: 300,
          height: 200,
        }
      } else {
        newNodes[nodeId] = nodes[nodeId]
      }
    })

    setNodes(newNodes)
  }, [model?.sheets.map((s) => s.name).join(",") || ""])

  const handleMouseDown = useCallback(
    (e: React.MouseEvent, nodeId: string, isPropertyPort?: boolean, propName?: string) => {
      e.preventDefault()
      e.stopPropagation()

      if (!model) return

      if (isPropertyPort && propName) {
        const rect = canvasRef.current?.getBoundingClientRect()
        if (!rect) return

        const node = nodes[nodeId]
        if (!node) return

        const nodeConfig = model.sheets.find((s) => s.name === nodeId)
        if (!nodeConfig) return

        const propIndex = (nodeConfig.properties || []).findIndex((p) => p.name === propName)
        const startPosition = {
          x: node.position.x - 6,
          y: node.position.y + 60 + propIndex * 30,
        }

        setDragState({
          isDragging: false,
          isConnecting: true,
          sourceNode: nodeId,
          sourceProp: propName,
          connectionLine: {
            start: startPosition,
            current: { x: e.clientX - rect.left, y: e.clientY - rect.top },
          },
        })
      } else {
        const rect = canvasRef.current?.getBoundingClientRect()
        if (!rect) return

        const node = nodes[nodeId]
        if (!node) return

        setDragState({
          isDragging: true,
          nodeId,
          offset: {
            x: e.clientX - rect.left - node.position.x,
            y: e.clientY - rect.top - node.position.y,
          },
        })
      }
    },
    [nodes, model],
  )

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const rect = canvasRef.current?.getBoundingClientRect()
      if (!rect) return

      if (dragState.isDragging && dragState.nodeId && dragState.offset) {
        const newPosition = {
          x: e.clientX - rect.left - dragState.offset.x,
          y: e.clientY - rect.top - dragState.offset.y,
        }

        setNodes((prev) => ({
          ...prev,
          [dragState.nodeId!]: {
            ...prev[dragState.nodeId!],
            position: newPosition,
          },
        }))
      } else if (dragState.isConnecting && dragState.connectionLine) {
        setDragState((prev) => ({
          ...prev,
          connectionLine: prev.connectionLine
            ? {
              ...prev.connectionLine,
              current: { x: e.clientX - rect.left, y: e.clientY - rect.top },
            }
            : undefined,
        }))
      }
    },
    [dragState],
  )

  const handleMouseUp = useCallback(
    (e: React.MouseEvent, targetNodeId?: string, targetProp?: string) => {
      if (!model) return

      if (dragState.isConnecting && dragState.sourceNode && dragState.sourceProp && targetNodeId && targetProp) {
        const targetNode = model.sheets.find((s) => s.name === targetNodeId)
        if (targetNode && targetProp === targetNode.unique_property) {
          createOrUpdateRef(dragState.sourceNode, dragState.sourceProp, targetNodeId)
        }
      }

      setDragState({ isDragging: false })
    },
    [dragState, model, createOrUpdateRef],
  )

  const handleInfoClick = useCallback(
    (e: React.MouseEvent, nodeId: string) => {
      e.preventDefault()
      e.stopPropagation()
      selectNode(nodeId)

      const node = nodes[nodeId]
      if (node && onSelectionChange) {
        onSelectionChange(node.position, node.width)
      }
    },
    [selectNode, onSelectionChange, nodes],
  )

  const handleEdgeLabelClick = useCallback(
    (e: React.MouseEvent, sourceNodeId: string, propName: string) => {
      e.preventDefault()
      e.stopPropagation()
      selectNode(sourceNodeId)

      const node = nodes[sourceNodeId]
      if (node && onSelectionChange) {
        onSelectionChange(node.position, node.width)
      }
    },
    [selectNode, onSelectionChange, nodes],
  )

  const handleDeleteClick = useCallback(
    (e: React.MouseEvent, nodeId: string) => {
      e.preventDefault()
      e.stopPropagation()
      deleteSheet(nodeId)
    },
    [deleteSheet],
  )

  const handleCanvasClick = useCallback(() => {
    clearSelection()
  }, [clearSelection])

  const handleAddNode = useCallback(() => {
    if (!model) return

    const existingNames = model.sheets.map((s) => s.name)
    let counter = 1
    let newName = `Sheet${counter}`
    while (existingNames.includes(newName)) {
      counter++
      newName = `Sheet${counter}`
    }
    addSheet(newName)
  }, [model, addSheet])

  const renderEdges = () => {
    if (!model) return []

    const edges: JSX.Element[] = []

    model.sheets.forEach((sheetConfig) => {
      const sheetName = sheetConfig.name
        ; (sheetConfig.properties || []).forEach((prop, propIndex) => {
          if (prop.kind === "ref") {
            const sourceNode = nodes[sheetName]
            const targetNode = nodes[prop.to]

            if (sourceNode && targetNode) {
              const sourceX = sourceNode.position.x - 6
              const sourceY = sourceNode.position.y + 60 + propIndex * 30
              const targetX = targetNode.position.x + targetNode.width + 6
              const targetY = targetNode.position.y + 60

              const edgeId = `${sheetName}.${prop.name}`
              const targetSheetConfig = model.sheets.find((s) => s.name === prop.to)
              const isInvalid = prop.on !== targetSheetConfig?.unique_property

              edges.push(
                <g key={edgeId}>
                  <line
                    x1={sourceX}
                    y1={sourceY}
                    x2={targetX}
                    y2={targetY}
                    stroke={isInvalid ? "hsl(var(--destructive))" : "hsl(var(--primary))"}
                    strokeWidth="2"
                    className="cursor-pointer hover:stroke-primary/80"
                  />
                  <text
                    x={(sourceX + targetX) / 2}
                    y={(sourceY + targetY) / 2 - 5}
                    textAnchor="middle"
                    className="text-xs fill-foreground cursor-pointer hover:fill-primary font-medium"
                    onClick={(e) => handleEdgeLabelClick(e, sheetName, prop.name)}
                  >
                    {prop.edge}
                  </text>
                </g>,
              )
            }
          }
        })
    })

    return edges
  }

  if (!model) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-background">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">No project selected</p>
          <p className="text-sm text-muted-foreground/70">Create or select a project to get started</p>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full h-full relative overflow-hidden bg-background" onClick={handleCanvasClick}>
      <div className="absolute top-4 left-4 z-10">
        <button
          className="w-10 h-10 bg-primary hover:bg-primary/90 text-primary-foreground rounded-full flex items-center justify-center shadow-lg transition-colors"
          onClick={handleAddNode}
          title="Add Node"
        >
          <Plus className="h-5 w-5" />
        </button>
      </div>

      <div
        ref={canvasRef}
        className="w-full h-full relative"
        onMouseMove={handleMouseMove}
        onMouseUp={(e) => handleMouseUp(e)}
      >
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1 }}>
          {renderEdges()}

          {dragState.isConnecting && dragState.connectionLine && (
            <line
              x1={dragState.connectionLine.start.x}
              y1={dragState.connectionLine.start.y}
              x2={dragState.connectionLine.current.x}
              y2={dragState.connectionLine.current.y}
              stroke="hsl(var(--primary))"
              strokeWidth="2"
              strokeDasharray="5,5"
            />
          )}
        </svg>

        {model.sheets.map((sheetConfig) => {
          const sheetName = sheetConfig.name
          const node = nodes[sheetName]
          if (!node) return null

          return (
            <div
              key={sheetName}
              className="absolute bg-card border border-border rounded-lg shadow-lg"
              style={{
                left: node.position.x,
                top: node.position.y,
                width: node.width,
                zIndex: 2,
              }}
              onMouseDown={(e) => handleMouseDown(e, sheetName)}
            >
              <div className="p-3 border-b bg-muted/50 rounded-t-lg">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium">{sheetName}</h3>
                  <div className="flex items-center gap-2">
                    <button
                      className="p-1 hover:bg-muted rounded"
                      onClick={(e) => handleInfoClick(e, sheetName)}
                      title="Node Info"
                    >
                      <Info className="h-4 w-4 text-muted-foreground" />
                    </button>
                    <button
                      className="p-1 hover:bg-destructive/10 rounded"
                      onClick={(e) => handleDeleteClick(e, sheetName)}
                      title="Delete Node"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </button>
                  </div>
                </div>
              </div>

              <div className="p-3 space-y-2 max-h-40 overflow-y-auto">
                {(sheetConfig.properties || []).map((prop) => {
                  const isUnique = prop.name === sheetConfig.unique_property
                  const isRef = prop.kind === "ref"

                  return (
                    <div key={`${sheetName}-${prop.name}`} className="flex items-center gap-2 text-xs relative">
                      <div
                        className="w-3 h-3 bg-primary rounded-full cursor-pointer hover:bg-primary/80 absolute -left-6"
                        onMouseDown={(e) => handleMouseDown(e, sheetName, true, prop.name)}
                        onClick={(e) => e.stopPropagation()}
                        title="Drag to create connection"
                      />


                      <div className="flex items-center gap-1 flex-1">
                        {isUnique && <Star className="h-3 w-3 text-amber-600 fill-amber-600" />}
                        <span className="font-medium">{prop.name}</span>
                        <span className="text-muted-foreground">{isRef ? `→ ${prop.to}` : prop.dtype}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      <div className="absolute bottom-4 left-4 flex gap-2" style={{ zIndex: 4 }}>
        <button
          className="px-3 py-1 bg-card border border-border rounded shadow text-xs hover:bg-muted"
          onClick={() => {
            if (!model) return

            const nodeEntries = model.sheets.map((s) => s.name)
            const newNodes: Record<string, CanvasNode> = {}
            nodeEntries.forEach((nodeId, index) => {
              newNodes[nodeId] = {
                id: nodeId,
                position: {
                  x: 50 + (index % 3) * 320,
                  y: 50 + Math.floor(index / 3) * 220,
                },
                width: 300,
                height: 200,
              }
            })
            setNodes(newNodes)
          }}
        >
          Reset Layout
        </button>
      </div>
    </div>
  )
}
