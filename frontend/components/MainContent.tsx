"use client"

import { useEffect } from "react"
import { ReactFlowGraphCanvas } from "@/components/canvas/ReactFlowGraphCanvas"
import { useSchemaStore } from "@/store/useSchemaStore"
import { WebSocketChat } from "@/components/websocket-chat"

export function MainContent() {
    const { activeTab, loadFromBackend, isLoading } = useSchemaStore()

    // Load projects from backend on mount
    useEffect(() => {
        loadFromBackend()
    }, [loadFromBackend])

    // Show loading state
    if (isLoading) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-background">
                <div className="text-center">
                    <p className="text-muted-foreground mb-4">Loading projects...</p>
                </div>
            </div>
        )
    }

    if (activeTab === "Editor") {
        return <ReactFlowGraphCanvas />
    }

    if (activeTab === "Graph") {
        <div className="w-full h-full flex items-center justify-center bg-background">
            <div className="text-center">
                <p className="text-muted-foreground mb-4">Loading projects...</p>
            </div>
        </div>
    }

    if (activeTab === "Chat") {
        return (
            <div
                className="w-full h-full relative"
            >
                <WebSocketChat />
            </div>
        )
    }

    return null
}
