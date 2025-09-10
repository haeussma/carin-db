"use client"

import { useState } from "react"
import { Toaster } from "@/components/ui/toaster"
import { ReactFlowGraphCanvas } from "@/components/canvas/ReactFlowGraphCanvas"
import { JsonPanel } from "@/components/json/JsonPanel"
import { NodeInspector } from "@/components/inspector/NodeInspector"
import { EdgeInspector } from "@/components/inspector/EdgeInspector"
import { TopBar } from "@/components/layout/TopBar"
import { useSchemaStore } from "@/store/useSchemaStore"

export default function SchemaDesigner() {
    const { selected } = useSchemaStore()
    const [inspectorOpen, setInspectorOpen] = useState(false)
    const [inspectorPosition, setInspectorPosition] = useState<{ x: number; y: number; side: "left" | "right" }>({
        x: 0,
        y: 0,
        side: "right",
    })

    const handleInspectorOpen = (nodePosition: { x: number; y: number }, nodeWidth: number) => {
        const viewportWidth = window.innerWidth
        const inspectorWidth = 500 // Width of the inspector popup
        const margin = 20

        // Determine if inspector should appear on left or right
        const spaceOnRight = viewportWidth - (nodePosition.x + nodeWidth + margin)
        const spaceOnLeft = nodePosition.x - margin

        let side: "left" | "right" = "right"
        let x = nodePosition.x + nodeWidth + margin

        if (spaceOnRight < inspectorWidth && spaceOnLeft >= inspectorWidth) {
            side = "left"
            x = nodePosition.x - inspectorWidth - margin
        }

        setInspectorPosition({
            x: Math.max(margin, Math.min(x, viewportWidth - inspectorWidth - margin)),
            y: Math.max(margin, nodePosition.y),
            side,
        })
        setInspectorOpen(true)
    }

    return (
        <div className="h-screen flex flex-col bg-background">
            <TopBar />

            <div className="flex-1 flex overflow-hidden">
                {/* Main Content */}
                <div className="flex-1 flex flex-col">
                    {/* Canvas */}
                    <div className="flex-1 relative">
                        <ReactFlowGraphCanvas />

                        {inspectorOpen && (
                            <>
                                {/* Backdrop */}
                                <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40" onClick={() => setInspectorOpen(false)} />

                                {/* Inspector Card */}
                                <div
                                    className="fixed bg-card border border-border rounded-lg shadow-xl z-50 w-[500px] max-h-[600px] overflow-y-auto"
                                    style={{
                                        left: inspectorPosition.x,
                                        top: inspectorPosition.y,
                                    }}
                                >
                                    {selected?.type === "node" && selected.id && (
                                        <NodeInspector nodeId={selected.id} onClose={() => setInspectorOpen(false)} />
                                    )}
                                    {selected?.type === "edge" && selected.id && (
                                        <EdgeInspector edgeId={selected.id} onClose={() => setInspectorOpen(false)} />
                                    )}
                                </div>
                            </>
                        )}
                    </div>

                    {/* Bottom Panel */}
                    <div className="h-80 border-t">
                        <JsonPanel />
                    </div>
                </div>
            </div>

            <Toaster />
        </div>
    )
}
