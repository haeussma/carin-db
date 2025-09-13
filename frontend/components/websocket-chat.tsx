"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronDown, ChevronRight, Send, Loader2, Eye, EyeOff } from "lucide-react"
import { cn } from "@/lib/utils"

interface ChatStep {
    id: string
    title: string
    content: string
    type: "step" | "final"
    isComplete: boolean
}

interface ChatMessage {
    id: string
    type: "user" | "assistant"
    content: string
    steps?: ChatStep[]
    currentStep?: string
    isStreaming?: boolean
}

interface WebSocketChatProps {
    wsUrl?: string
    className?: string
    mockMode?: boolean
}

export function WebSocketChat({ wsUrl = "ws://localhost:8080", className, mockMode = false }: WebSocketChatProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([])
    const [input, setInput] = useState("")
    const [isConnected, setIsConnected] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [currentStep, setCurrentStep] = useState<string>("")
    const [collapsedSteps, setCollapsedSteps] = useState<Set<string>>(new Set())
    const [allowDataAccess, setAllowDataAccess] = useState(false)

    const wsRef = useRef<WebSocket | null>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const isDemoMode = mockMode || wsUrl.includes("demo")

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    useEffect(() => {
        if (isDemoMode) {
            const timer = setTimeout(() => {
                setIsConnected(true)
                console.log("Demo mode: Simulated connection")
            }, 1000)

            return () => {
                clearTimeout(timer)
                setIsConnected(false)
            }
        } else {
            connectWebSocket()
            return () => {
                if (wsRef.current) {
                    wsRef.current.close()
                    wsRef.current = null
                }
            }
        }
    }, [wsUrl, isDemoMode])

    const connectWebSocket = () => {
        if (isDemoMode) {
            console.log("Prevented WebSocket creation in demo mode")
            return
        }

        try {
            wsRef.current = new WebSocket(wsUrl)

            wsRef.current.onopen = () => {
                setIsConnected(true)
                console.log("Real WebSocket connected")
            }

            wsRef.current.onmessage = (event) => {
                const data = JSON.parse(event.data)
                handleWebSocketMessage(data)
            }

            wsRef.current.onclose = () => {
                setIsConnected(false)
                setIsLoading(false)
                setCurrentStep("")
                console.log("Real WebSocket disconnected")
            }

            wsRef.current.onerror = (error) => {
                console.error("Real WebSocket error:", error)
                setIsConnected(false)
                setIsLoading(false)
            }
        } catch (error) {
            console.error("Failed to connect real WebSocket:", error)
            setIsConnected(false)
            setIsLoading(false)
        }
    }

    const handleWebSocketMessage = (data: any) => {
        switch (data.type) {
            case "step_start":
                setCurrentStep(data.step)
                break
            case "step_content":
                updateCurrentMessage(data.stepId, data.content, false)
                break
            case "step_complete":
                updateCurrentMessage(data.stepId, data.content, true)
                setCurrentStep("")
                break
            case "final_response":
                addFinalResponse(data.content)
                setIsLoading(false)
                setCurrentStep("")
                break
            case "error":
                console.error("WebSocket message error:", data.message)
                setIsLoading(false)
                setCurrentStep("")
                break
        }
    }

    const updateCurrentMessage = (stepId: string, content: string, isComplete: boolean) => {
        setMessages((prev) => {
            const lastMessage = prev[prev.length - 1]
            if (lastMessage && lastMessage.type === "assistant") {
                const updatedSteps =
                    lastMessage.steps?.map((step) => (step.id === stepId ? { ...step, content, isComplete } : step)) || []

                return [...prev.slice(0, -1), { ...lastMessage, steps: updatedSteps }]
            }
            return prev
        })
    }

    const addFinalResponse = (content: string) => {
        setMessages((prev) => {
            const lastMessage = prev[prev.length - 1]
            if (lastMessage && lastMessage.type === "assistant") {
                const finalStep: ChatStep = {
                    id: "final",
                    title: "Final Answer",
                    content,
                    type: "final",
                    isComplete: true,
                }

                return [
                    ...prev.slice(0, -1),
                    {
                        ...lastMessage,
                        steps: [...(lastMessage.steps || []), finalStep],
                        isStreaming: false,
                    },
                ]
            }
            return prev
        })
    }

    const sendMessage = () => {
        if (!input.trim() || !isConnected || isLoading) return

        const userMessage: ChatMessage = {
            id: Date.now().toString(),
            type: "user",
            content: input.trim(),
        }

        const assistantMessage: ChatMessage = {
            id: (Date.now() + 1).toString(),
            type: "assistant",
            content: "",
            steps: [],
            isStreaming: true,
        }

        setMessages((prev) => [...prev, userMessage, assistantMessage])
        setInput("")
        setIsLoading(true)

        if (isDemoMode) {
            window.dispatchEvent(
                new CustomEvent("mockWebSocketMessage", {
                    detail: {
                        type: "message",
                        content: userMessage.content,
                        allowDataAccess: allowDataAccess,
                    },
                }),
            )
        } else if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(
                JSON.stringify({
                    type: "message",
                    content: userMessage.content,
                    allowDataAccess: allowDataAccess,
                }),
            )
        }
    }

    const toggleStepCollapse = (stepId: string) => {
        setCollapsedSteps((prev) => {
            const newSet = new Set(prev)
            if (newSet.has(stepId)) {
                newSet.delete(stepId)
            } else {
                newSet.add(stepId)
            }
            return newSet
        })
    }

    const renderContent = (content: string, type: "markdown" | "table" | "code" | "text" = "text") => {
        switch (type) {
            case "markdown":
                return (
                    <div className="markdown-content prose prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: content }} />
                )
            case "code":
                return (
                    <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                        <code className="font-mono text-sm">{content}</code>
                    </pre>
                )
            case "table":
                return (
                    <div className="overflow-x-auto">
                        <div dangerouslySetInnerHTML={{ __html: content }} />
                    </div>
                )
            default:
                return <p className="leading-relaxed whitespace-pre-wrap">{content}</p>
        }
    }

    useEffect(() => {
        if (isDemoMode) {
            const handleMockMessage = (event: any) => {
                handleWebSocketMessage(event.detail)
            }

            window.addEventListener("mockWebSocketResponse", handleMockMessage)
            return () => {
                window.removeEventListener("mockWebSocketResponse", handleMockMessage)
            }
        }
    }, [isDemoMode])

    return (
        <div className={cn("flex flex-col h-screen bg-background", className)}>
            {/* Header */}
            <div className="border-b border-border p-4 bg-card">
                <div className="max-w-4xl mx-auto flex items-center justify-between">
                    <h1 className="text-xl font-bold">AI Chat Assistant</h1>
                    <div className="flex items-center gap-4">
                        <div className="flex items-center space-x-2">
                            <Label htmlFor="data-access" className="text-sm font-medium">
                                Allow data access
                            </Label>
                            <Switch id="data-access" checked={allowDataAccess} onCheckedChange={setAllowDataAccess} />
                            {allowDataAccess ? (
                                <Eye className="w-4 h-4 text-green-600" />
                            ) : (
                                <EyeOff className="w-4 h-4 text-muted-foreground" />
                            )}
                        </div>
                        <div className="flex items-center gap-2">
                            <div className={cn("w-2 h-2 rounded-full", isConnected ? "bg-green-500" : "bg-red-500")} />
                            <span className="text-sm text-muted-foreground">
                                {isConnected ? "Connected" : "Disconnected"}
                                {isDemoMode && " (Demo)"}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Current Step Indicator */}
            {currentStep && (
                <div className="border-b border-border bg-accent/10 p-2">
                    <div className="max-w-4xl mx-auto flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin text-accent" />
                        <span className="text-sm font-medium text-accent">Current Step: {currentStep}</span>
                    </div>
                </div>
            )}

            {/* Chat Messages - Center 2/3 */}
            <div className="flex-1 overflow-y-auto">
                <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
                    {messages.map((message) => (
                        <div key={message.id} className={cn("flex", message.type === "user" ? "justify-end" : "justify-start")}>
                            <div
                                className={cn(
                                    "max-w-[80%] rounded-lg p-4",
                                    message.type === "user"
                                        ? "bg-primary text-primary-foreground ml-auto"
                                        : "bg-card border border-border",
                                )}
                            >
                                {message.type === "user" ? (
                                    <p className="leading-relaxed">{message.content}</p>
                                ) : (
                                    <div className="space-y-3">
                                        {message.steps?.map((step) => (
                                            <div key={step.id}>
                                                {step.type === "final" ? (
                                                    <div className="border-t border-border pt-4 mt-4">
                                                        <h3 className="font-semibold mb-3 text-foreground">{step.title}</h3>
                                                        <div className="text-foreground">{renderContent(step.content)}</div>
                                                    </div>
                                                ) : (
                                                    <Collapsible
                                                        open={!collapsedSteps.has(step.id)}
                                                        onOpenChange={() => toggleStepCollapse(step.id)}
                                                    >
                                                        <CollapsibleTrigger asChild>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                className="chat-step w-full justify-start p-2 h-auto text-left"
                                                            >
                                                                {collapsedSteps.has(step.id) ? (
                                                                    <ChevronRight className="w-4 h-4 mr-2 flex-shrink-0" />
                                                                ) : (
                                                                    <ChevronDown className="w-4 h-4 mr-2 flex-shrink-0" />
                                                                )}
                                                                <span className="text-sm font-medium">
                                                                    {step.title}
                                                                    {!step.isComplete && <span className="streaming-cursor ml-1" />}
                                                                </span>
                                                            </Button>
                                                        </CollapsibleTrigger>
                                                        <CollapsibleContent className="chat-step pl-6 pr-2 pb-2">
                                                            <div className="text-sm text-muted-foreground">
                                                                {renderContent(step.content)}
                                                                {!step.isComplete && <span className="streaming-cursor" />}
                                                            </div>
                                                        </CollapsibleContent>
                                                    </Collapsible>
                                                )}
                                            </div>
                                        ))}

                                        {message.isStreaming && message.steps?.length === 0 && (
                                            <div className="flex items-center gap-2 text-muted-foreground">
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                                <span className="text-sm">Thinking...</span>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Area */}
            <div className="border-t border-border p-4 bg-card">
                <div className="max-w-4xl mx-auto">
                    <div className="flex gap-2">
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Type your message..."
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                    e.preventDefault()
                                    sendMessage()
                                }
                            }}
                            disabled={!isConnected || isLoading}
                            className="flex-1"
                        />
                        <Button onClick={sendMessage} disabled={!isConnected || isLoading || !input.trim()} size="icon">
                            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    )
}
