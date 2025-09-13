"use client"

import { memo } from "react"
import { EdgeProps, getBezierPath, EdgeLabelRenderer, BaseEdge } from "@xyflow/react"
import { Button } from "@/components/ui/button"

export const ClickableEdge = memo(({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    style = {},
    data,
    markerEnd,
}: EdgeProps) => {
    const [edgePath, labelX, labelY] = getBezierPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
    })

    const handleEdgeClick = () => {
        console.log('🔗 Edge clicked:', id)
        // You can add your edge click logic here
        // For example, open an edge inspector or show edge details
    }

    return (
        <>
            <BaseEdge
                id={id}
                path={edgePath}
                markerEnd={markerEnd}
                style={style}
            />
            <EdgeLabelRenderer>
                <div
                    style={{
                        position: 'absolute',
                        transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
                        fontSize: 12,
                        pointerEvents: 'all',
                    }}
                    className="nodrag nopan"
                >
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleEdgeClick}
                        className="h-6 px-2 text-xs bg-background/80 backdrop-blur-sm border-primary/50 hover:bg-primary/10"
                    >
                        {data?.label || id}
                    </Button>
                </div>
            </EdgeLabelRenderer>
        </>
    )
})

ClickableEdge.displayName = "ClickableEdge"
