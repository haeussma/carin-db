'use client'

import { useState, useEffect } from 'react'
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface SettingsDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
    const [activeTab, setActiveTab] = useState("openai")

    // OpenAI state
    const [apiKey, setApiKey] = useState('')
    const [isValidating, setIsValidating] = useState(false)
    const [apiError, setApiError] = useState<string | null>(null)
    const [apiSaved, setApiSaved] = useState(false)

    // Database state
    const [dbName, setDbName] = useState('')
    const [dbUrl, setDbUrl] = useState('')
    const [dbUsername, setDbUsername] = useState('')
    const [dbPassword, setDbPassword] = useState('')
    const [dbError, setDbError] = useState<string | null>(null)
    const [dbSaved, setDbSaved] = useState(false)

    // Load API info via endpoint
    useEffect(() => {
        fetch('http://localhost:8000/api/config/openai')
            .then(res => res.json())
            .then(data => {
                if (data.openai_api_key) {
                    setApiKey(data.openai_api_key)
                }
            })
            .catch(err => {
                console.error("Failed to fetch OpenAI key:", err)
            })
    }, [])

    // Load database settings via endpoint
    useEffect(() => {
        fetch('http://localhost:8000/api/config/database')
            .then(res => res.json())
            .then(data => {
                if (!data.error) {
                    setDbName(data.name)
                    setDbUrl(data.url)
                    setDbUsername(data.username)
                    // Display password as asterisks if it exists
                    if (data.password) {
                        setDbPassword('*'.repeat(data.password.length))
                    } else {
                        setDbPassword('')
                    }
                }
            })
            .catch(err => {
                console.error("Failed to fetch database settings:", err)
            })
    }, [])

    const handleSaveApiKey = async () => {
        if (!apiKey) {
            setApiError('API key is required')
            return
        }

        setIsValidating(true)
        setApiSaved(false)
        setApiError(null)

        try {
            const response = await fetch('http://localhost:8000/api/save_openai_key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ api_key: apiKey })
            })

            if (!response.ok) {
                const data = await response.json();
                let errorMessage = 'Failed to save API key';

                if (data.error && data.error.message) {
                    errorMessage = data.error.message;
                } else if (data.detail) {
                    if (typeof data.detail === 'object' && data.detail.error && data.detail.error.message) {
                        errorMessage = data.detail.error.message;
                    } else if (typeof data.detail === 'string') {
                        errorMessage = data.detail;
                    }
                }

                throw new Error(errorMessage);
            }

            // Show success message
            setApiSaved(true)

            // Don't close the dialog - just reset success state after delay
            // Do not use a timer if we have one elsewhere
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to save API key'
            console.error("Error saving API key:", errorMessage)
            setApiError(errorMessage)
            setApiSaved(false)
        } finally {
            setIsValidating(false)
        }
    }

    const handleSaveDbSettings = async () => {
        if (!dbUrl) {
            setDbError('Database URL is required')
            return
        }

        if (!dbName) {
            setDbError('Database name is required')
            return
        }

        setDbError(null)
        setDbSaved(false)

        try {
            const response = await fetch('http://localhost:8000/api/config/database', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: dbName,
                    url: dbUrl,
                    username: dbUsername,
                    password: dbPassword === '*'.repeat(dbPassword.length) ? null : dbPassword
                })
            })

            if (!response.ok) {
                const data = await response.json()
                throw new Error(data.error || data.detail || 'Failed to save database settings')
            }

            // Show success message
            setDbSaved(true)

            // Don't close the dialog - just reset success state after delay
            // Do not use a timer if we have one elsewhere
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to save database settings'
            console.error("Error saving DB settings:", errorMessage)
            setDbError(errorMessage)
        }
    }

    // Replace the conflicting useEffect with a single useEffect that handles success states
    // This is the only place we'll set timers for state reset
    useEffect(() => {
        // When apiSaved or dbSaved becomes true, set a timer to reset them after 2 seconds
        if (apiSaved) {
            const timer = setTimeout(() => {
                setApiSaved(false)
            }, 2000)
            return () => clearTimeout(timer)
        }
    }, [apiSaved])

    useEffect(() => {
        if (dbSaved) {
            const timer = setTimeout(() => {
                setDbSaved(false)
            }, 2000)
            return () => clearTimeout(timer)
        }
    }, [dbSaved])

    // Reset all states when dialog opens/closes
    useEffect(() => {
        if (!open) {
            // Reset states when dialog closes
            setApiSaved(false)
            setDbSaved(false)
            setApiError(null)
            setDbError(null)
        }
    }, [open])

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Settings</DialogTitle>
                </DialogHeader>

                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="openai">OpenAI</TabsTrigger>
                        <TabsTrigger value="database">Database</TabsTrigger>
                    </TabsList>

                    <TabsContent value="openai" className="space-y-4 mt-4">
                        <div className="space-y-2">
                            <Label htmlFor="apiKey">API Key</Label>
                            <Input
                                id="apiKey"
                                type="password"
                                value={apiKey}
                                onChange={(e) => {
                                    setApiKey(e.target.value)
                                    setApiError(null)
                                }}
                                placeholder="sk-..."
                            />
                            {apiError && (
                                <div className="text-sm text-red-500">{apiError}</div>
                            )}
                        </div>

                        <DialogFooter className="flex gap-2">
                            <Button
                                onClick={handleSaveApiKey}
                                className={`flex-1 ${apiSaved ? "bg-green-500 hover:bg-green-600" : ""}`}
                                disabled={isValidating || !apiKey}
                            >
                                {isValidating ? 'Validating......' : apiSaved ? 'Saved!' : 'Save API Settings'}
                            </Button>
                        </DialogFooter>
                    </TabsContent>

                    <TabsContent value="database" className="space-y-4 mt-4">
                        <div className="space-y-2">
                            <Label htmlFor="db-url">URL</Label>
                            <Input
                                id="db-url"
                                value={dbUrl}
                                onChange={(e) => {
                                    setDbUrl(e.target.value)
                                    setDbError(null)
                                }}
                                placeholder="bolt://localhost:7687"
                            />
                            <Label htmlFor="db-username">Username</Label>
                            <Input
                                id="db-username"
                                value={dbUsername}
                                onChange={(e) => setDbUsername(e.target.value)}
                                placeholder="neo4j"
                            />
                            <Label htmlFor="db-password">Password</Label>
                            <Input
                                id="db-password"
                                value={dbPassword}
                                onChange={(e) => setDbPassword(e.target.value)}
                                type="password"
                                placeholder="********"
                            />
                            {dbError && (
                                <div className="text-sm text-red-500">{dbError}</div>
                            )}
                        </div>

                        <DialogFooter className="flex gap-2">
                            <Button
                                onClick={handleSaveDbSettings}
                                className={`flex-1 ${dbSaved ? "bg-green-500 hover:bg-green-600" : ""}`}
                                disabled={!dbUrl || !dbName}
                            >
                                {dbSaved ? 'Saved!' : 'Save DB Settings'}
                            </Button>
                        </DialogFooter>
                    </TabsContent>
                </Tabs>
            </DialogContent>
        </Dialog>
    )
} 