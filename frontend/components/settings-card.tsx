"use client"

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface SettingsCardProps {
    onClose: () => void
}

export function SettingsCard({ onClose }: SettingsCardProps) {
    const [apiKey, setApiKey] = useState('')
    const [isValidating, setIsValidating] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [dbAddress, setDbAddress] = useState('')
    const [dbPassword, setDbPassword] = useState('')

    // Load API key from localStorage on component mount
    useEffect(() => {
        const savedKey = localStorage.getItem('openai_api_key')
        if (savedKey) {
            setApiKey(savedKey)
        }
    }, [])

    const validateApiKey = async (key: string) => {
        setIsValidating(true)
        setError(null)
        try {
            const response = await fetch('/api/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-OpenAI-Key': key
                },
                body: JSON.stringify({ question: 'test' })
            })

            if (!response.ok) {
                const data = await response.json()
                throw new Error(data.error || data.detail || 'Invalid API key')
            }

            return true
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to validate API key')
            return false
        } finally {
            setIsValidating(false)
        }
    }

    const handleSave = async () => {
        if (!apiKey) {
            setError('API key is required')
            return
        }

        if (await validateApiKey(apiKey)) {
            localStorage.setItem('openai_api_key', apiKey)
            onClose()
        }
    }

    const handleClear = () => {
        localStorage.removeItem('openai_api_key')
        setApiKey('')
        setError(null)
    }

    return (
        <div className="w-full max-w-lg border rounded-lg shadow-sm">
            <div className="flex flex-row items-center justify-between p-4 border-b">
                <h2 className="text-2xl font-bold">Settings</h2>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onClose}
                    className="rounded-full"
                >
                    <X className="h-4 w-4" />
                </Button>
            </div>
            <div className="p-4 space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="apiKey">OpenAI API Key</Label>
                    <Input
                        id="apiKey"
                        type="password"
                        value={apiKey}
                        onChange={(e) => {
                            setApiKey(e.target.value)
                            setError(null)
                        }}
                        placeholder="sk-..."
                    />
                    {error && (
                        <div className="text-sm text-red-500">{error}</div>
                    )}
                </div>
                <div className="space-y-2">
                    <Label htmlFor="db-address">URL</Label>
                    <Input
                        id="db-address"
                        value={dbAddress}
                        onChange={(e) => setDbAddress(e.target.value)}
                        placeholder="bolt://localhost:7687"
                    />
                    <Label htmlFor="db-address">Username</Label>
                    <Input
                        id="db-address"
                        value={dbAddress}
                        onChange={(e) => setDbAddress(e.target.value)}
                        placeholder="neo4j"
                    />
                    <Label htmlFor="db-password">Password</Label>
                    <Input
                        id="db-password"
                        value={dbPassword}
                        onChange={(e) => setDbPassword(e.target.value)}
                        type="password"
                        placeholder=""
                    />
                </div>
                <div className="flex gap-2">
                    <Button
                        onClick={handleSave}
                        className="flex-1"
                        disabled={isValidating || !apiKey}
                    >
                        {isValidating ? 'Validating...' : 'Save Settings'}
                    </Button>
                    <Button
                        onClick={handleClear}
                        variant="outline"
                        disabled={!apiKey}
                    >
                        Clear
                    </Button>
                </div>
            </div>
        </div>
    )
}
