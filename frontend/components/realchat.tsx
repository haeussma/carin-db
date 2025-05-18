"use client"

import { useRef, useEffect, useState } from "react"
import { Send } from "lucide-react"

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    type?: "intermediate" | "final" | "error";
}

interface WebSocketResponse {
    type: "intermediate" | "final" | "error";
    content: string;
    needs_input?: boolean;
}

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [socket, setSocket] = useState<WebSocket | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Initialize WebSocket connection
        const ws = new WebSocket("ws://localhost:8000/llm_chat");

        ws.onopen = () => {
            console.log("Connected to WebSocket");
            setIsConnected(true);
            // Add a welcome message
            setMessages([{
                id: Date.now().toString(),
                role: "assistant",
                content: "Hello! I'm your EnzymeML Mapping Assistant. How can I help you today?",
                type: "intermediate"
            }]);
        };

        ws.onmessage = (event) => {
            const response: WebSocketResponse = JSON.parse(event.data);

            setMessages(prev => [...prev, {
                id: Date.now().toString(),
                role: "assistant",
                content: response.content,
                type: response.type
            }]);

            setIsLoading(false);

            // If we got a final response, we can close the connection
            if (response.type === "final") {
                ws.close();
            }
        };

        ws.onerror = (error) => {
            console.error("WebSocket error:", error);
            setMessages(prev => [...prev, {
                id: Date.now().toString(),
                role: "assistant",
                content: "Sorry, there was an error in the connection.",
                type: "error"
            }]);
            setIsLoading(false);
            setIsConnected(false);
        };

        ws.onclose = () => {
            console.log("WebSocket connection closed");
            setSocket(null);
            setIsConnected(false);
        };

        setSocket(ws);

        // Cleanup on component unmount
        return () => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.close();
            }
        };
    }, []);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setInput(e.target.value);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || !socket || !isConnected) return;

        // Add user message to chat
        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: input
        };
        setMessages(prev => [...prev, userMessage]);
        setInput("");
        setIsLoading(true);

        try {
            // Send message through WebSocket as JSON
            const message = {
                type: "user_input",
                content: input
            };
            socket.send(JSON.stringify(message));
        } catch (error) {
            console.error("Error sending message:", error);
            setMessages(prev => [...prev, {
                id: Date.now().toString(),
                role: "assistant",
                content: "Sorry, there was an error sending your message. Please try again.",
                type: "error"
            }]);
            setIsLoading(false);
        }
    };

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages]);

    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-50 p-4">
            <div className="w-full max-w-2xl bg-white rounded-xl shadow-lg overflow-hidden border border-gray-200">
                {/* Chat header */}
                <div className="bg-white border-b border-gray-200 p-4">
                    <h2 className="text-lg font-medium">EnzymeML Mapping Assistant</h2>
                    {!isConnected && (
                        <p className="text-sm text-red-500 mt-1">Connecting to server...</p>
                    )}
                </div>

                {/* Chat messages */}
                <div className="h-[60vh] overflow-y-auto p-4 space-y-4">
                    {messages.length === 0 ? (
                        <div className="flex items-center justify-center h-full text-gray-500">
                            <p>Send a message to start the conversation</p>
                        </div>
                    ) : (
                        messages.map((message) => (
                            <div key={message.id} className={`${message.role === "user" ? "flex justify-end" : "w-full"}`}>
                                {message.role === "user" ? (
                                    <div className="max-w-[80%] rounded-lg p-3 bg-blue-500 text-white rounded-br-none">
                                        {message.content}
                                    </div>
                                ) : (
                                    <div className={`w-[98%] mx-auto border rounded-md p-4 ${message.type === "error"
                                        ? "border-red-200 bg-red-50 text-red-800"
                                        : message.type === "final"
                                            ? "border-green-200 bg-green-50 text-green-800"
                                            : "border-gray-200 bg-gray-50 text-gray-800"
                                        }`}>
                                        {message.content}
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                    {isLoading && (
                        <div className="w-[98%] mx-auto border border-gray-200 rounded-md p-4 bg-gray-50 text-gray-800">
                            <div className="flex space-x-2">
                                <div
                                    className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
                                    style={{ animationDelay: "0ms" }}
                                ></div>
                                <div
                                    className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
                                    style={{ animationDelay: "150ms" }}
                                ></div>
                                <div
                                    className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
                                    style={{ animationDelay: "300ms" }}
                                ></div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Chat input */}
                <div className="border-t border-gray-200 p-4">
                    <form onSubmit={handleSubmit} className="flex space-x-2">
                        <input
                            type="text"
                            value={input}
                            onChange={handleInputChange}
                            placeholder={isConnected ? "Type your message..." : "Connecting..."}
                            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                            disabled={isLoading || !isConnected}
                        />
                        <button
                            type="submit"
                            className="bg-blue-500 text-white rounded-lg p-2 hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                            disabled={isLoading || !input.trim() || !isConnected}
                        >
                            <Send size={20} />
                        </button>
                    </form>
                </div>
            </div>
        </div>
    )
}
