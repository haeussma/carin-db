// InteractiveGraphVisualization.tsx
"use client";

import React, { useCallback, useEffect, useMemo } from "react";
import ReactFlow, {
    addEdge,
    Background,
    Controls,
    Handle,
    Node,
    Edge,
    Position,
    ConnectionLineType,
    useNodesState,
    useEdgesState,
    useReactFlow,
    ReactFlowProvider,
    NodeProps
} from "reactflow";
import "reactflow/dist/style.css";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

//
// Type Definitions
//
interface Column {
    name: string;
    data_type: string;
}

interface Sheet {
    name: string;
    columns: Column[];
}

export interface SheetModel {
    sheets: Sheet[];
}

export interface SheetConnection {
    source_sheet_name: string;
    target_sheet_name: string;
    edge_name: string;
    key: string;
}

export interface SheetReference {
    source_sheet_name: string;
    source_column_name: string;
    target_sheet_name: string;
    target_column_name: string;
}

interface InteractiveGraphVisualizationProps {
    sheetModel: SheetModel;
    sheetConnections: SheetConnection[];
    sheetReferences: SheetReference[];
}

//
// Custom Node Component with Tooltip
//
const CustomNode: React.FC<NodeProps> = ({ data }) => (
    <TooltipProvider>
        <Tooltip>
            <TooltipTrigger asChild>
                <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-stone-400">
                    <div className="font-bold">{data.label}</div>
                </div>
            </TooltipTrigger>
            <TooltipContent>
                <div className="max-w-md">
                    <h3 className="font-bold mb-2">{data.label} Attributes:</h3>
                    <ul className="list-disc pl-4">
                        {data.attributes &&
                            data.attributes.map((attr: Column, idx: number) => (
                                <li key={idx}>
                                    {attr.name}: {attr.data_type}
                                </li>
                            ))}
                    </ul>
                </div>
            </TooltipContent>
        </Tooltip>
        <Handle type="target" position={Position.Top} className="w-16 !bg-teal-500" />
        <Handle type="source" position={Position.Bottom} className="w-16 !bg-teal-500" />
    </TooltipProvider>
);

const nodeTypes = { custom: CustomNode };

//
// Flow Component: Creates and updates nodes/edges from props
//
const Flow: React.FC<InteractiveGraphVisualizationProps> = ({
    sheetModel,
    sheetConnections,
    sheetReferences,
}) => {
    const { fitView } = useReactFlow();

    // Compute nodes from sheetModel.sheets
    const computedNodes: Node[] = useMemo(() => {
        return sheetModel.sheets.map((sheet, index) => ({
            id: sheet.name,
            type: "custom",
            position: { x: (index % 3) * 250, y: Math.floor(index / 3) * 200 },
            data: { label: sheet.name, attributes: sheet.columns },
        }));
    }, [sheetModel]);

    // Compute edges from sheetConnections and sheetReferences
    const computedEdges: Edge[] = useMemo(() => {
        const connectionEdges: Edge[] = sheetConnections.map((conn, idx) => ({
            id: `e-conn-${idx}`,
            source: conn.source_sheet_name,
            target: conn.target_sheet_name,
            label: conn.edge_name,
            type: "smoothstep",
            animated: true,
        }));
        const referenceEdges: Edge[] = sheetReferences.map((ref, idx) => ({
            id: `e-ref-${idx}`,
            source: ref.source_sheet_name,
            target: ref.target_sheet_name,
            label: `${ref.source_column_name} -> ${ref.target_column_name}`,
            type: "smoothstep",
            style: { stroke: "#f6ad55" },
        }));
        return [...connectionEdges, ...referenceEdges];
    }, [sheetConnections, sheetReferences]);

    const [nodes, setNodes, onNodesChange] = useNodesState(computedNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(computedEdges);

    // Update nodes/edges when computed values change
    useEffect(() => {
        setNodes(computedNodes);
    }, [computedNodes, setNodes]);

    useEffect(() => {
        setEdges(computedEdges);
    }, [computedEdges, setEdges]);

    const onConnect = useCallback(
        (params: any) => setEdges((eds) => addEdge(params, eds)),
        [setEdges]
    );

    useEffect(() => {
        // Ensure the view is fitted after rendering
        const timer = setTimeout(() => {
            fitView({ padding: 0.2 });
        }, 0);
        return () => clearTimeout(timer);
    }, [fitView, nodes, edges]);

    return (
        <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-left"
            connectionLineType={ConnectionLineType.SmoothStep}
        >
            <Background />
            <Controls />
        </ReactFlow>
    );
};

//
// Main Component
//
const InteractiveGraphVisualization: React.FC<InteractiveGraphVisualizationProps> = (props) => {
    return (
        <Card className="w-full max-w-4xl h-[600px]">
            <CardHeader>
                <CardTitle>Interactive Graph Visualization</CardTitle>
                <CardDescription>
                    Live view of your sheet model, connections, and references.
                </CardDescription>
            </CardHeader>
            <CardContent className="h-[500px]">
                <ReactFlowProvider>
                    <Flow {...props} />
                </ReactFlowProvider>
            </CardContent>
        </Card>
    );
};

export default InteractiveGraphVisualization;
