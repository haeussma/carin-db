// MultiEdge.tsx
import React from "react";
import { getSmoothStepPath, EdgeProps } from "reactflow";

const MultiEdge: React.FC<EdgeProps> = ({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    style,
    label,
    data,
    markerEnd,
}) => {
    // Use the offset from data; default to 0 if not provided
    const offset = data?.offset || 0;

    // Adjust the y-coordinates (or x, depending on your layout) by the offset
    const adjustedSourceY = sourceY + offset;
    const adjustedTargetY = targetY + offset;

    // getSmoothStepPath helps to create a smooth curve between adjusted coordinates
    const [edgePath, labelX, labelY] = getSmoothStepPath({
        sourceX,
        sourceY: adjustedSourceY,
        targetX,
        targetY: adjustedTargetY,
        sourcePosition,
        targetPosition,
    });

    return (
        <>
            <path
                id={id}
                style={style}
                className="react-flow__edge-path"
                d={edgePath}
                markerEnd={markerEnd}
            />
            {label && (
                <text>
                    <textPath href={`#${id}`} startOffset="50%" textAnchor="middle">
                        {label}
                    </textPath>
                </text>
            )}
        </>
    );
};

export default MultiEdge;
