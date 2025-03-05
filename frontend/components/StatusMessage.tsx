import React, { useState } from "react"
import { AlertCircle, CheckCircle, X } from "lucide-react"

interface StatusMessageProps {
    message: string
    type?: "success" | "error" | "info"
}

export function StatusMessage({ message, type = "info" }: StatusMessageProps) {
    const [isVisible, setIsVisible] = useState(true)

    if (!message || !isVisible) return null

    const getIcon = () => {
        switch (type) {
            case "success":
                return <CheckCircle className="h-4 w-4" />
            case "error":
                return <AlertCircle className="h-4 w-4" />
            default:
                return <AlertCircle className="h-4 w-4" />
        }
    }

    const getColorClass = () => {
        switch (type) {
            case "success":
                return "bg-green-50 text-green-700 border-green-200"
            case "error":
                return "bg-red-50 text-red-700 border-red-200"
            default:
                return "bg-blue-50 text-blue-700 border-blue-200"
        }
    }

    return (
        <div className={`mt-4 p-4 rounded-md border ${getColorClass()} relative`}>
            <button
                onClick={() => setIsVisible(false)}
                className="absolute top-2 right-2 hover:bg-gray-200 hover:bg-opacity-50 rounded-full p-1"
                aria-label="Close message"
            >
                <X className="h-4 w-4" />
            </button>
            <div className="flex items-start pr-6">
                <div className="flex-shrink-0 mt-0.5">{getIcon()}</div>
                <div className="ml-3">
                    {message.includes("<br/>") ? (
                        <div dangerouslySetInnerHTML={{ __html: message }} />
                    ) : (
                        message
                    )}
                </div>
            </div>
        </div>
    )
} 