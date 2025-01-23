'use client'

import { useState } from 'react'
import { Send } from 'lucide-react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Card, CardContent } from './ui/card'

export function Chat() {
    const [message, setMessage] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!message.trim()) return

        const apiKey = localStorage.getItem('openai_api_key')
        if (!apiKey) {
            setError('Please set your OpenAI API key in settings first')
            return
        }

        setLoading(true)
        setError(null)

        try {
            const response = await fetch('http://localhost:8000/api/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-OpenAI-Key': apiKey
                },
                body: JSON.stringify({ question: message })
            })

            if (!response.ok) {
                const errorData = await response.json()
                throw new Error(errorData.error || errorData.detail || 'Request failed')
            }

            const data = await response.json()
            // Handle the response data here
            console.log(data)

        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred')
        } finally {
            setLoading(false)
        }
    }

    return (
        <Card className="w-full max-w-2xl mx-auto">
            <CardContent className="p-4">
                {error && (
                    <div className="text-red-500 mb-4 text-sm">{error}</div>
                )}
                <form onSubmit={handleSubmit} className="flex gap-2">
                    <Input
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        placeholder="Ask a question..."
                        disabled={loading}
                    />
                    <Button type="submit" disabled={loading}>
                        {loading ? 'Sending...' : <Send className="h-4 w-4" />}
                    </Button>
                </form>
            </CardContent>
        </Card>
    )
} 