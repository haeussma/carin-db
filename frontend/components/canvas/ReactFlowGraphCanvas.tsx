"use client"

import React, { useCallback, useMemo, useEffect, useState } from 'react'
import {
    ReactFlow,
    useNodesState,
    useEdgesState,
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
import { Button } from '@/components/ui/button'
import { Plus, Upload, Save } from 'lucide-react'

const nodeTypes = {
    sheetNode: SheetCardNode as any,
}

// Component that uses useReactFlow hook inside ReactFlow context
function ReactFlowControls({ nodes, isMounted }: { nodes: Node[], isMounted: boolean }) {
    const { fitView } = useReactFlow()

    // Auto-fit view when nodes change - ensures all content is always reachable
    React.useEffect(() => {
        if (nodes.length > 0 && isMounted) {
            // Small delay to ensure React Flow is ready
            const timer = setTimeout(() => {
                fitView({
                    padding: 0.2,  // 20% padding for breathing room
                    includeHiddenNodes: false
                })
            }, 100)
            return () => clearTimeout(timer)
        }
    }, [nodes, isMounted, fitView])

    return null
}

export function ReactFlowGraphCanvas() {
    const { getCurrentModel, selectNode, selectEdge, clearSelection, createOrUpdateRef, updateSheetPosition, addSheet, removeProperty, replaceSheetConnection } = useSchemaStore()
    const [propertyInspectorOpen, setPropertyInspectorOpen] = React.useState(false)
    const [selectedProperty, setSelectedProperty] = React.useState<{ nodeId: string, propertyName: string } | null>(null)
    const [isConnecting, setIsConnecting] = React.useState(false)
    const [isMounted, setIsMounted] = useState(false)
    const connectionStartRef = React.useRef<{ nodeId: string, handleId: string, position: { x: number, y: number } } | null>(null)
    const model = getCurrentModel()


    // Prevent hydration mismatches by only rendering after mount
    useEffect(() => {
        setIsMounted(true)
    }, [])


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
        if (!model) {
            return []
        }

        const nodes = model.sheets.map((sheet, index) => {
            // Use stored position or calculate deterministic fallback
            const defaultPosition = {
                x: 50 + (index % 3) * 350,
                y: 50 + Math.floor(index / 3) * 250,
            }

            const node = {
                id: sheet.name,
                type: 'sheetNode',
                position: sheet.position || defaultPosition,
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
            }

            return node
        })

        return nodes
    }, [model, handlePropertyEdit, isConnecting])


    // Convert our model to React Flow edges
    const initialEdges: Edge[] = useMemo(() => {
        if (!model) return []

        const edges: Edge[] = []

        model.sheets.forEach((sheet) => {
            sheet.properties.forEach((prop, propIndex) => {
                if (prop.kind === 'ref') {
                    // Create unique edge ID using sheet name, property name, and target
                    const edgeId = `${sheet.name}.${prop.name}.${prop.to}.${propIndex}`
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
            console.log('🔗 onConnect called with:', params)

            if (!params.source || !params.target || !params.sourceHandle || !params.targetHandle) {
                console.log('❌ Missing required params:', { source: params.source, target: params.target, sourceHandle: params.sourceHandle, targetHandle: params.targetHandle })
                return
            }

            // Extract property names from handle IDs
            const sourceProp = params.sourceHandle.replace('-source', '')
            const targetProp = params.targetHandle.replace('-target', '')

            console.log('📝 Extracted properties:', { sourceProp, targetProp, from: `${params.source}.${sourceProp}`, to: `${params.target}.${targetProp}` })

            // Remove existing connections between the same two sheets and create new one atomically
            if (model) {
                console.log('📊 Model found, checking for source sheet:', params.source)
                const sourceSheet = model.sheets.find(s => s.name === params.source)
                if (sourceSheet) {
                    console.log('✅ Source sheet found:', sourceSheet.name, 'properties count:', sourceSheet.properties.length)

                    // Check if there are existing ref properties that connect to the same target sheet
                    const existingRefs = sourceSheet.properties.filter(prop =>
                        prop.kind === 'ref' && prop.to === params.target
                    )

                    console.log('🔍 Found existing refs to target:', existingRefs.length, existingRefs.map(r => r.name))

                    if (existingRefs.length > 0) {
                        console.log(`🔄 Replacing ${existingRefs.length} existing connection(s) between ${params.source} -> ${params.target}`)

                        // Use atomic replace function instead of remove + create
                        console.log('🔄 Calling replaceSheetConnection:', params.source, sourceProp, params.target, targetProp)
                        replaceSheetConnection(params.source, sourceProp, params.target, targetProp)
                    } else {
                        // No existing connections, just create new one
                        console.log(`✨ Creating new connection between ${params.source} -> ${params.target}`)
                        console.log('🔄 Calling createOrUpdateRef:', params.source, sourceProp, params.target, targetProp)
                        createOrUpdateRef(params.source, sourceProp, params.target, targetProp)
                    }
                } else {
                    // Source sheet not found, fallback to create
                    console.log('❌ Source sheet not found, fallback to create')
                    createOrUpdateRef(params.source, sourceProp, params.target, targetProp)
                }
            } else {
                // No model, fallback to create
                console.log('❌ No model found, fallback to create')
                createOrUpdateRef(params.source, sourceProp, params.target, targetProp)
            }

            // Don't manually add edge - let the model regeneration handle it
            // The edge will be automatically created when the model updates

            // Automatically open PropertyInspector for the newly created reference
            setTimeout(() => {
                setSelectedProperty({ nodeId: params.source, propertyName: sourceProp })
                setPropertyInspectorOpen(true)
            }, 100) // Small delay to ensure the property is created in the store
        },
        [createOrUpdateRef, removeProperty, replaceSheetConnection, model]
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

                    const sourcePropName = connectionStartRef.current.handleId.replace('-source', '')
                    const sourceNodeId = connectionStartRef.current.nodeId

                    // Create a new sheet at this position (same as plus button)
                    console.log('🆕 Creating new sheet at position:', { x: x - 160, y: y - 100 })
                    const newSheetName = addSheet(undefined, { x: x - 160, y: y - 100 })

                    console.log('🔗 Creating reference from', sourceNodeId, sourcePropName, 'to', newSheetName, 'with edge HAS_' + sourcePropName.toUpperCase())

                    // Create the reference with custom edge name "HAS_{source_property_label}"
                    // This will connect to the new sheet's 'id' property
                    createOrUpdateRef(sourceNodeId, sourcePropName, newSheetName, 'id', `HAS_${sourcePropName.toUpperCase()}`)

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

    const handleAddNewNode = useCallback(() => {
        // Calculate center position of the current viewport
        const canvasCenter = {
            x: 400, // Approximate center X
            y: 300  // Approximate center Y
        }

        // Add a new sheet at the center
        return addSheet(undefined, canvasCenter)
    }, [addSheet])

    const handleUploadExcel = useCallback(() => {
        // Create file input element
        const input = document.createElement('input')
        input.type = 'file'
        input.accept = '.xlsx,.xls'
        input.onchange = (e) => {
            const file = (e.target as HTMLInputElement).files?.[0]
            if (file) {
                console.log('📊 Excel file selected:', file.name)
                // TODO: Implement Excel parsing and sheet/node creation
                // This would parse the Excel file and create nodes for each sheet
            }
        }
        input.click()
    }, [])

    const handleSaveSchema = useCallback(() => {
        console.log('💾 Saving schema to backend...')
        // TODO: Implement schema sync to backend
        // This would send the current schema state to the backend
    }, [])

    // Only show loading if we truly don't have a model or aren't mounted
    // Add a small delay to prevent flickering during state updates
    const [showLoading, setShowLoading] = useState(true)

    useEffect(() => {
        if (model && isMounted) {
            // Small delay to prevent flickering during rapid state updates
            const timer = setTimeout(() => setShowLoading(false), 100)
            return () => clearTimeout(timer)
        } else {
            setShowLoading(true)
        }
    }, [model, isMounted])

    if (showLoading) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-background">
                <div className="text-center">
                    <p className="text-muted-foreground mb-4">{!model ? "No project selected" : "Loading..."}</p>
                    <p className="text-sm text-muted-foreground/70">{!model ? "Create or select a project to get started" : "Initializing canvas..."}</p>
                </div>
            </div>
        )
    }

    return (
        <div
            className="w-full h-full relative"
        >
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

            {/* Action Buttons - Top Left */}
            {/* 
                Align the first button (Add) to the left, and the other two (Upload, Save) to the right.
                We use two absolutely positioned containers: one left, one right, both top-aligned.
            */}
            <div>
                {/* Left-aligned Add button */}
                <div className="absolute top-4 left-4 z-50 flex">
                    <Button
                        onClick={handleAddNewNode}
                        className="h-12 w-12 rounded-full bg-primary hover:bg-primary/90 shadow-lg"
                        title="Add new sheet node"
                        size="sm"
                    >
                        <Plus className="h-5 w-5" />
                    </Button>
                </div>
                {/* Right-aligned Upload and Save buttons */}
                <div className="absolute top-4 right-4 z-50 flex gap-2">
                    <Button
                        onClick={handleUploadExcel}
                        className="h-12 w-12 rounded-full bg-secondary hover:bg-secondary/90 shadow-lg"
                        title="Upload Excel file"
                        size="sm"
                    >
                        <Upload className="h-5 w-5" />
                    </Button>
                    <Button
                        onClick={handleSaveSchema}
                        className="h-12 w-12 rounded-full bg-green-600 hover:bg-green-700 shadow-lg"
                        title="Save schema to backend"
                        size="sm"
                    >
                        <Save className="h-5 w-5" />
                    </Button>
                </div>
            </div>

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
                fitViewOptions={{
                    padding: 0.2,  // 20% padding around content for breathing room
                    includeHiddenNodes: false,
                }}
                translateExtent={[[-5000, -5000], [5000, 5000]]}  // Large panning area
                minZoom={0.1}
                maxZoom={2}
                attributionPosition="bottom-left"
                className="bg-background w-full h-full"
                style={{ width: '100%', height: '100%' }}
            >
                <Background color="hsl(var(--muted))" gap={20} />
                <Controls className="bg-card border border-border" />
                <MiniMap
                    className="bg-card border border-border"
                    nodeStrokeColor="hsl(var(--primary))"
                    nodeColor="hsl(var(--card))"
                    maskColor="hsl(var(--background) / 0.8)"
                    style={{ width: 120, height: 80 }}
                />
                <ReactFlowControls nodes={nodes} isMounted={isMounted} />
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
