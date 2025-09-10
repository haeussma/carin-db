"use client"

import React, { useCallback, useMemo } from 'react'
import {
    ReactFlow,
    useNodesState,
    useEdgesState,
    addEdge,
    MiniMap,
    Controls,
    Background,
    ConnectionMode,
    useReactFlow,
    type Node,
    type Edge,
    type Connection,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useSchemaStore } from '@/store/useSchemaStore'
import { SheetCardNode } from '@/components/nodes/SheetCardNode'
import { PropertyInspector } from '@/components/inspector/PropertyInspector'

const nodeTypes = {
    sheetNode: SheetCardNode as any,
}

export function ReactFlowGraphCanvas() {
    const { getCurrentModel, selectNode, selectEdge, clearSelection, createOrUpdateRef, updateSheetPosition, addSheet } = useSchemaStore()
    const [propertyInspectorOpen, setPropertyInspectorOpen] = React.useState(false)
    const [selectedProperty, setSelectedProperty] = React.useState<{ nodeId: string, propertyName: string } | null>(null)
    const [isConnecting, setIsConnecting] = React.useState(false)
    const connectionStartRef = React.useRef<{ nodeId: string, handleId: string, position: { x: number, y: number } } | null>(null)
    const model = getCurrentModel()

    const handlePropertyEdit = useCallback((nodeId: string, propertyName: string) => {
        setSelectedProperty({ nodeId, propertyName })
        setPropertyInspectorOpen(true)
    }, [])

    const handleClosePropertyInspector = useCallback(() => {
        setPropertyInspectorOpen(false)
        setSelectedProperty(null)
    }, [])

    // Convert our model to React Flow nodes
    const initialNodes: Node[] = useMemo(() => {
        if (!model) return []

        return model.sheets.map((sheet, index) => ({
            id: sheet.name,
            type: 'sheetNode',
            position: sheet.position || {
                x: 50 + (index % 3) * 350,
                y: 50 + Math.floor(index / 3) * 250,
            },
            data: {
                nodeName: sheet.name,
                nodeConfig: {
                    sheet: sheet.name,
                    unique_property: sheet.unique_property,
                    properties: sheet.properties.reduce((acc, prop) => {
                        acc[prop.name] = prop
                        return acc
                    }, {} as Record<string, any>),
                },
                onPropertyEdit: handlePropertyEdit,
                isConnecting: isConnecting,
            },
        }))
    }, [model, handlePropertyEdit, isConnecting])

    // Convert our model to React Flow edges
    const initialEdges: Edge[] = useMemo(() => {
        if (!model) return []

        const edges: Edge[] = []

        model.sheets.forEach((sheet) => {
            sheet.properties.forEach((prop) => {
                if (prop.kind === 'ref') {
                    const edgeId = `${sheet.name}.${prop.name}`
                    edges.push({
                        id: edgeId,
                        source: sheet.name,
                        target: prop.to,
                        sourceHandle: `${prop.name}-source`,
                        targetHandle: `${prop.on}-target`,
                        animated: true,
                        style: {
                            stroke: 'hsl(var(--primary))',
                            strokeWidth: 2,
                        },
                        label: prop.edge,
                        labelStyle: {
                            fontSize: 12,
                            fill: 'hsl(var(--foreground))',
                        },
                        labelBgStyle: {
                            fill: 'hsl(var(--background))',
                            fillOpacity: 0.8,
                        },
                    } as Edge)
                }
            })
        })

        return edges
    }, [model])

    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

    // Update nodes and edges when model changes
    React.useEffect(() => {
        setNodes(initialNodes)
    }, [initialNodes, setNodes])

    React.useEffect(() => {
        setEdges(initialEdges)
    }, [initialEdges, setEdges])

    const onConnect = useCallback(
        (params: Connection) => {
            if (!params.source || !params.target || !params.sourceHandle || !params.targetHandle) {
                return
            }

            // Extract property names from handle IDs
            const sourceProp = params.sourceHandle.replace('-source', '')
            const targetProp = params.targetHandle.replace('-target', '')

            // Create the reference in the store
            createOrUpdateRef(params.source, sourceProp, params.target)

            // Create a new edge with animation
            const newEdge: Edge = {
                ...params,
                id: `${params.source}.${sourceProp}`,
                animated: true,
                style: {
                    stroke: 'hsl(var(--primary))',
                    strokeWidth: 2,
                },
                label: `${sourceProp.toUpperCase()}_TO_${params.target?.toUpperCase()}`,
                labelStyle: {
                    fontSize: 12,
                    fill: 'hsl(var(--foreground))',
                },
                labelBgStyle: {
                    fill: 'hsl(var(--background))',
                    fillOpacity: 0.8,
                },
            }

            setEdges((eds) => addEdge(newEdge, eds))

            // Automatically open PropertyInspector for the newly created reference
            setTimeout(() => {
                setSelectedProperty({ nodeId: params.source, propertyName: sourceProp })
                setPropertyInspectorOpen(true)
            }, 100) // Small delay to ensure the property is created in the store
        },
        [setEdges, createOrUpdateRef]
    )

    const onNodeClick = useCallback(
        (event: React.MouseEvent, node: Node) => {
            selectNode(node.id)
        },
        [selectNode]
    )

    const onEdgeClick = useCallback(
        (event: React.MouseEvent, edge: Edge) => {
            selectEdge(edge.id)
        },
        [selectEdge]
    )

    const onPaneClick = useCallback(() => {
        clearSelection()
    }, [clearSelection])

    const onConnectStart = useCallback((event: any, { nodeId, handleId, handleType }: any) => {
        console.log('🚀 Connection started:', { nodeId, handleId, handleType })
        setIsConnecting(true)
        if (nodeId && handleId && handleType === 'source') {
            // Get the mouse/touch position
            const clientX = event.touches ? event.touches[0].clientX : event.clientX
            const clientY = event.touches ? event.touches[0].clientY : event.clientY

            const startData = {
                nodeId,
                handleId,
                position: { x: clientX, y: clientY }
            }
            console.log('💾 Saving connection start data:', startData)
            connectionStartRef.current = startData
        }
    }, [])

    const onConnectEnd = useCallback((event: any) => {
        console.log('🛑 Connection ended - checking if successful or dropped on empty space')
        console.log('🔍 Current connectionStart ref:', connectionStartRef.current)

        setIsConnecting(false)

        // Use current connectionStart ref directly
        if (connectionStartRef.current) {
            console.log('✅ Have connection start data, checking drop target...')

            // Get the final mouse/touch position
            const clientX = event.changedTouches ? event.changedTouches[0].clientX : event.clientX || event.clientX
            const clientY = event.changedTouches ? event.changedTouches[0].clientY : event.clientY || event.clientY

            console.log('🖱️ Drop coordinates:', { clientX, clientY })

            // Check if the drop target is empty space (not on another node)
            const elementAtPosition = document.elementFromPoint(clientX, clientY)
            const isOnNode = elementAtPosition?.closest('.react-flow__node')

            console.log('🔍 Element at position:', elementAtPosition)
            console.log('🎯 Is on node?', !!isOnNode)

            if (!isOnNode) {
                console.log('🎯 Connection dropped on empty space!')
                console.log('ConnectionStart:', connectionStartRef.current)

                // Get React Flow viewport coordinates
                const reactFlowWrapper = document.querySelector('.react-flow')
                const viewport = document.querySelector('.react-flow__viewport')

                if (reactFlowWrapper && viewport) {
                    const wrapperRect = reactFlowWrapper.getBoundingClientRect()

                    // Get transform from viewport
                    const transform = window.getComputedStyle(viewport).transform
                    let scale = 1
                    let translateX = 0
                    let translateY = 0

                    if (transform && transform !== 'none') {
                        const matrix = transform.match(/matrix\((.+)\)/)
                        if (matrix) {
                            const values = matrix[1].split(', ').map(Number)
                            scale = values[0]
                            translateX = values[4]
                            translateY = values[5]
                        }
                    }

                    // Convert screen coordinates to flow coordinates
                    const x = (clientX - wrapperRect.left - translateX) / scale
                    const y = (clientY - wrapperRect.top - translateY) / scale

                    console.log('📍 Drop position (flow coords):', { x, y, scale, translateX, translateY })

                    // Create a new sheet at this position
                    const sourcePropName = connectionStartRef.current.handleId.replace('-source', '')

                    // Generate a name based on the source property
                    const baseName = sourcePropName.charAt(0).toUpperCase() + sourcePropName.slice(1).replace(/([A-Z])/g, ' $1').trim()
                    const newSheetName = `${baseName} Target`

                    console.log('🆕 Creating new sheet:', newSheetName, 'at position:', { x: x - 160, y: y - 100 })

                    // Add the new sheet with the calculated position (offset to center the node)
                    addSheet(newSheetName, { x: x - 160, y: y - 100 })

                    const sourceNodeId = connectionStartRef.current.nodeId
                    console.log('🔗 Creating reference from', sourceNodeId, sourcePropName, 'to', newSheetName, 'id')

                    // Create the reference from the source property to the new sheet's 'id' property
                    createOrUpdateRef(sourceNodeId, sourcePropName, newSheetName, 'id')

                    // Automatically open PropertyInspector for the newly created reference
                    setTimeout(() => {
                        setSelectedProperty({ nodeId: sourceNodeId, propertyName: sourcePropName })
                        setPropertyInspectorOpen(true)
                    }, 100)
                } else {
                    console.error('❌ Could not find .react-flow or .react-flow__viewport element')
                }
            } else {
                console.log('🎯 Connection dropped on existing node')
            }
        } else {
            console.log('❌ No connection start data found')
        }

        connectionStartRef.current = null
    }, [addSheet, createOrUpdateRef])

    const onNodeDragStop = useCallback(
        (event: React.MouseEvent, node: Node) => {
            // Update the stored position when user stops dragging a node
            updateSheetPosition(node.id, node.position)
        },
        [updateSheetPosition]
    )

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
        <div className="w-full h-full">
            {/* Custom styles for React Flow handles */}
            <style jsx global>{`
                .react-flow__handle {
                    z-index: 1000 !important;
                    pointer-events: all !important;
                }
                .react-flow__handle-top,
                .react-flow__handle-bottom,
                .react-flow__handle-left,
                .react-flow__handle-right {
                    z-index: 1000 !important;
                }
            `}</style>

            {/* Connection Mode Indicator */}
            {isConnecting && (
                <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-50 bg-primary text-primary-foreground px-4 py-2 rounded-lg shadow-lg">
                    <p className="text-sm font-medium">Drag to connect properties</p>
                </div>
            )}


            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onConnectStart={onConnectStart}
                onConnectEnd={onConnectEnd}
                onNodeClick={onNodeClick}
                onEdgeClick={onEdgeClick}
                onPaneClick={onPaneClick}
                onNodeDragStop={onNodeDragStop}
                nodeTypes={nodeTypes}
                connectionMode={ConnectionMode.Loose}
                fitView
                attributionPosition="bottom-left"
                className="bg-background"
            >
                <Background color="hsl(var(--muted))" gap={20} />
                <Controls className="bg-card border border-border" />
                <MiniMap
                    className="bg-card border border-border"
                    nodeStrokeColor="hsl(var(--primary))"
                    nodeColor="hsl(var(--card))"
                    maskColor="hsl(var(--background) / 0.8)"
                />
            </ReactFlow>

            {/* Property Inspector Overlay */}
            {propertyInspectorOpen && selectedProperty && (
                <>
                    {/* Backdrop */}
                    <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40" onClick={handleClosePropertyInspector} />

                    {/* Property Inspector Card */}
                    <div className="fixed bg-card border border-border rounded-lg shadow-xl z-50 w-[500px] max-h-[600px] overflow-y-auto top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                        <PropertyInspector
                            nodeId={selectedProperty.nodeId}
                            propertyName={selectedProperty.propertyName}
                            onClose={handleClosePropertyInspector}
                        />
                    </div>
                </>
            )}
        </div>
    )
}
