import { cn } from "@/lib/utils"

interface StatusMessageProps {
    message: string
    color?: string
}

export const StatusMessage = ({ message, color = "" }: StatusMessageProps) => {
    if (!message) return null

    return (
        <div
            className={cn(
                "px-4 py-2 rounded-md text-sm font-medium",
                color ? `bg-${color}-100 text-${color}-700` : "bg-gray-100 text-gray-700",
            )}
        >
            {message}
        </div>
    )
}

