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
    type Node,
    type Edge,
    type Connection,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useSchemaStore } from '@/store/useSchemaStore'
import { SheetCardNode } from '@/components/nodes/SheetCardNode'
import { PropertyInspector } from '@/components/inspector/PropertyInspector'
import { SpreadsheetErrorDialog } from '@/components/spreadsheet-error-dialog'
import { Button } from '@/components/ui/button'
import { Plus, Upload, Save } from 'lucide-react'
import { ApiError } from '@/lib/api'
import { EdgeInspector } from '@/components/inspector/EdgeInspector'

const nodeTypes = {
    sheetNode: SheetCardNode as any,
}

// Component that uses useReactFlow hook inside ReactFlow context
function ReactFlowControls({ nodes, isMounted }: { nodes: Node[], isMounted: boolean }) {
    return null
}

export function ReactFlowGraphCanvas() {
    const {
        getCurrentProject,
        selectNode, selectEdge, clearSelection,
        createOrUpdateRef, updateSheetPosition, addSheet, addProperty, removeProperty, replaceSheetConnection,
        saveToBackend, importSchema,
        isLoading, isSyncing,
        currentProjectName,
        projects,
    } = useSchemaStore()
    const [propertyInspectorOpen, setPropertyInspectorOpen] = React.useState(false)
    const [selectedProperty, setSelectedProperty] = React.useState<{ nodeId: string, propertyName: string } | null>(null)
    const [isConnecting, setIsConnecting] = React.useState(false)
    const [isMounted, setIsMounted] = useState(false)
    const [spreadsheetError, setSpreadsheetError] = React.useState<any>(null)
    const [errorDialogOpen, setErrorDialogOpen] = React.useState(false)
    const [showEdgeInspector, setShowEdgeInspector] = useState(false)
    const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
    const connectionStartRef = React.useRef<{ nodeId: string, handleId: string, position: { x: number, y: number } } | null>(null)
    const project = getCurrentProject()

    // Debug logging
    useEffect(() => {
        console.log('🎨 Canvas state updated:', {
            currentProjectName,
            projectsCount: projects.length,
            projectNames: projects.map(p => p.project_name),
            model: !!project
        })
        if (project) {
            console.log('📊 Model sheets:', project.sheets.length, project.sheets.map(s => s.name))
        }
    }, [project, currentProjectName, projects])

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
        if (!project) {
            return []
        }

        // Debug: Check for duplicate sheet names
        const sheetNames = project.sheets.map(s => s.name)
        const duplicates = sheetNames.filter((name, index) => sheetNames.indexOf(name) !== index)
        if (duplicates.length > 0) {
            console.error('🚨 Duplicate sheet names detected:', duplicates)
            console.error('📊 All sheet names:', sheetNames)
            console.error('📊 Model:', project)
        }

        const nodes = project.sheets.map((sheet, index) => {
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
                    sheetNode: sheet,
                    onPropertyEdit: handlePropertyEdit,
                    isConnecting: isConnecting,
                },
            }

            return node
        })

        return nodes
    }, [project, handlePropertyEdit, isConnecting])


    // Convert our model to React Flow edges
    const initialEdges: Edge[] = useMemo(() => {
        if (!project) return []

        const edges: Edge[] = []

        console.log('🔍 Edge creation debug - Model sheets:', project.sheets.length)
        project.sheets.forEach((sheet) => {
            console.log(`📊 Sheet "${sheet.name}" has ${sheet.properties.length} properties:`)
            sheet.properties.forEach((prop, propIndex) => {
                console.log(`  - Property "${prop.name}": kind="${prop.kind}"`, prop.kind === 'ref' ? `-> ${prop.to}.${prop.on}` : '')
                if (prop.kind === 'ref') {
                    // Create unique edge ID using sheet name, property name, and target
                    const sourceHandleId = `${sheet.name}-${prop.name}-source`
                    const targetHandleId = `${prop.to}-${prop.on}-target`
                    const edgeId = `${sheet.name}.${prop.name}.${prop.to}.${prop.on}`

                    console.log('🚀 Creating edge:', {
                        sheetName: sheet.name,
                        propName: prop.name,
                        targetSheet: prop.to,
                        targetProp: prop.on,
                        sourceHandleId,
                        targetHandleId,
                        edgeId
                    })
                    edges.push({
                        id: edgeId,
                        source: sheet.name,
                        target: prop.to,
                        type: 'smoothstep',
                        sourceHandle: `${sheet.name}-${prop.name}-source`,
                        targetHandle: `${prop.to}-${prop.on}-target`,
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

        console.log(`🎯 Total edges created: ${edges.length}`)
        if (edges.length > 0) {
            console.log('📋 Edge details:', edges.map(e => ({
                id: e.id,
                source: e.source,
                target: e.target,
                sourceHandle: e.sourceHandle,
                targetHandle: e.targetHandle
            })))
        }

        return edges
    }, [project])

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
            const sourceProp = params.sourceHandle.replace(`${params.source}-`, '').replace('-source', '')
            const targetProp = params.targetHandle.replace(`${params.target}-`, '').replace('-target', '')

            console.log('📝 Extracted properties:', { sourceProp, targetProp, from: `${params.source}.${sourceProp}`, to: `${params.target}.${targetProp}` })

            // Remove existing connections between the same two sheets and create new one atomically
            if (project) {
                console.log('📊 Model found, checking for source sheet:', params.source)
                const sourceSheet = project.sheets.find(s => s.name === params.source)
                if (sourceSheet) {
                    console.log('✅ Source sheet found:', sourceSheet.name, 'properties count:', sourceSheet.properties.length)

                    // Check if there are existing ref properties from the SAME source property to the target sheet
                    const existingRefs = sourceSheet.properties.filter(prop =>
                        prop.kind === 'ref' && prop.to === params.target && prop.name === sourceProp
                    )

                    console.log('🔍 Found existing refs from same source property to target:', existingRefs.length, existingRefs.map(r => r.name))

                    if (existingRefs.length > 0) {
                        console.log(`🔄 Replacing existing connection from ${params.source}.${sourceProp} -> ${params.target}`)

                        // Use atomic replace function instead of remove + create
                        console.log('🔄 Calling replaceSheetConnection:', params.source, sourceProp, params.target, targetProp)
                        replaceSheetConnection(params.source, sourceProp, params.target, targetProp)
                    } else {
                        // No existing connections from this source property, just create new one
                        console.log(`✨ Creating new connection between ${params.source}.${sourceProp} -> ${params.target}.${targetProp}`)
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
        },
        [createOrUpdateRef, removeProperty, replaceSheetConnection, project]
    )

    const onNodeClick = useCallback(
        (event: React.MouseEvent, node: Node) => {
            selectNode(node.id)
        },
        [selectNode]
    )

    const onEdgeClick = useCallback(
        (event: React.MouseEvent, edge: Edge) => {
            console.log('🔗 Edge clicked:', edge.id, edge.data)
            setSelectedEdgeId(edge.id)
            setShowEdgeInspector(true)
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
        const input = document.createElement('input')
        input.type = 'file'
        input.accept = '.xlsx'
        input.onchange = async (e) => {
            const file = (e.target as HTMLInputElement).files?.[0]
            if (!file) return
            const inputElement = e.target as HTMLInputElement
            try {
                console.log('📊 Excel file selected:', file.name)

                // Import the schema into the current project
                console.log('🔍 Importing into current project:', currentProjectName)
                await importSchema(file, currentProjectName!)
                console.log(`✅ Imported schema into project: ${currentProjectName}`)

            } catch (err) {
                console.error('❌ Import failed:', err)

                // Handle 422 validation errors with detailed dialog
                if (err instanceof ApiError && err.status === 422) {
                    try {
                        const errorDetails = JSON.parse(err.message)
                        // Backend returns {detail: {error: "spreadsheet_validation", ...}}
                        // Extract the actual error object from detail
                        const validationError = errorDetails.detail || errorDetails
                        setSpreadsheetError(validationError)
                        setErrorDialogOpen(true)
                    } catch {
                        // Fallback if error message isn't valid JSON
                        alert('Spreadsheet validation failed. Please check your file format.')
                    }
                } else {
                    // Handle other errors with simple alert
                    alert(err instanceof Error ? err.message : 'Import failed')
                }
            } finally {
                inputElement.value = ''
            }
        }
        input.click()
    }, [importSchema])

    const handleSaveSchema = useCallback(async () => {
        try {
            console.log('💾 Saving schema to backend...')
            await saveToBackend() // uses currentProjectId internally
        } catch (err) {
            console.error('❌ Save failed:', err)
            alert(err instanceof Error ? err.message : 'Save failed')
        }
    }, [saveToBackend])

    // Only show loading if we truly don't have a model or aren't mounted
    // Add a small delay to prevent flickering during state updates
    const [showLoading, setShowLoading] = useState(true)

    useEffect(() => {
        if (project && isMounted) {
            // Small delay to prevent flickering during rapid state updates
            const timer = setTimeout(() => setShowLoading(false), 100)
            return () => clearTimeout(timer)
        } else {
            setShowLoading(true)
        }
    }, [project, isMounted])

    if (showLoading) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-background">
                <div className="text-center">
                    <p className="text-muted-foreground mb-4">Loading...</p>
                    <p className="text-sm text-muted-foreground/70">Initializing canvas...</p>
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
                    .react - flow__handle {
                        z- index: 1000!important;
                pointer - events: all!important;
            }
                .react - flow__handle - top,
                .react - flow__handle - bottom,
                .react - flow__handle - left,
                .react - flow__handle - right {
        z - index: 1000!important;
    }
    `}</style>

            {/* Action Buttons - Top Left */}
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
                        disabled={isLoading || isSyncing}
                        className="h-12 w-12 rounded-full bg-secondary hover:bg-secondary/90 shadow-lg"
                        title="Upload Excel file"
                        size="sm"
                    >
                        <Upload className="h-5 w-5" />
                    </Button>

                    <Button
                        onClick={handleSaveSchema}
                        disabled={isSyncing}
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
                attributionPosition="bottom-right"
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
                {/* Remove this line: */}
                {/* <ReactFlowControls nodes={nodes} isMounted={isMounted} /> */}
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

            {/* Spreadsheet Error Dialog */}
            <SpreadsheetErrorDialog
                error={spreadsheetError}
                open={errorDialogOpen}
                onOpenChange={setErrorDialogOpen}
            />

            {/* Edge Inspector */}
            {selectedEdgeId && (
                <EdgeInspector
                    edgeId={selectedEdgeId}
                    open={showEdgeInspector}
                    onOpenChange={(open) => {
                        setShowEdgeInspector(open)
                        if (!open) setSelectedEdgeId(null)
                    }}
                />
            )}
        </div>
    )
}
