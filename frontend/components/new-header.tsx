"use client"

import { Button } from "@/components/ui/button"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ChevronDown, Plus, Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { useSchemaStore } from "@/store/useSchemaStore"
import React, { useState } from "react"

export function Header() {
    const {
        projects,
        currentProjectName,
        activeTab,
        setActiveTab,
        createProject,
        deleteProject,
        selectProject,
        syncWithBackend,
        isLoading,
    } = useSchemaStore()

    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
    const [newProjectName, setNewProjectName] = useState("")

    // Auto-open create dialog when no projects exist
    React.useEffect(() => {
        if (!isLoading && projects.length === 0 && !isCreateDialogOpen) {
            setIsCreateDialogOpen(true)
        }
    }, [isLoading, projects.length, isCreateDialogOpen])

    const currentProject = currentProjectName
        ? projects.find(p => p.name === currentProjectName)
        : null

    const handleCreateProject = async () => {
        const name = newProjectName.trim()
        if (!name) return

        try {
            const projectName = await createProject(name)
            console.log("Created project:", projectName)
            setNewProjectName(projectName)
            console.log("Set current project name:", projectName)
            setIsCreateDialogOpen(false)
        } catch (error) {
            console.error("Failed to create project:", error)
        }
    }

    const handleDeleteProject = async (projectName: string) => {
        if (projects.length <= 1) {
            console.log("Cannot delete the last project")
            return
        }
        await deleteProject(projectName)
        console.log("Deleted project:", projectName)
    }

    const handleRefreshProjects = async () => {
        await syncWithBackend()
        console.log("Refreshed projects from backend")
    }
    return (
        <header className="w-full h-16 border-b bg-background flex items-center px-4 relative">
            {/* Left section - Project Management */}
            <div className="flex items-center gap-2">
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline" className="justify-between min-w-[160px] bg-transparent">
                            <span className="truncate">
                                {currentProject?.name || (isLoading ? "Loading..." : "Select Project")}
                            </span>
                            <ChevronDown className="h-4 w-4 ml-2 flex-shrink-0" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="w-[200px]">
                        {projects.map((project) => (
                            <DropdownMenuItem
                                key={project.name}
                                onClick={() => selectProject(project.name)}
                                className="flex items-center justify-between"
                            >
                                <span className="truncate">{project.name}</span>
                                {projects.length > 1 && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-6 w-6 p-0 hover:bg-destructive hover:text-destructive-foreground"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            handleDeleteProject(project.name)
                                        }}
                                    >
                                        <Trash2 className="h-3 w-3" />
                                    </Button>
                                )}
                            </DropdownMenuItem>
                        ))}
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={handleRefreshProjects}>
                            Refresh Projects
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>

                <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
                    <DialogTrigger asChild>
                        <Button
                            variant="outline"
                            size="sm"
                            className="flex-shrink-0 bg-transparent"
                        >
                            <Plus className="h-4 w-4" />
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[425px]">
                        <DialogHeader>
                            <DialogTitle>Create New Project</DialogTitle>
                        </DialogHeader>
                        <div className="grid gap-4 py-4">
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="project-name" className="text-right">
                                    Name
                                </Label>
                                <Input
                                    id="project-name"
                                    value={newProjectName}
                                    onChange={(e) => setNewProjectName(e.target.value)}
                                    className="col-span-3"
                                    placeholder="Enter project name"
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter") {
                                            handleCreateProject()
                                        }
                                    }}
                                />
                            </div>
                        </div>
                        <div className="flex justify-end gap-2">
                            <Button
                                variant="outline"
                                onClick={() => {
                                    setIsCreateDialogOpen(false)
                                    setNewProjectName("")
                                }}
                            >
                                Cancel
                            </Button>
                            <Button
                                onClick={handleCreateProject}
                                disabled={!newProjectName.trim()}
                            >
                                Create Project
                            </Button>
                        </div>
                    </DialogContent>
                </Dialog>
            </div>

            {/* Center section - Tab Switcher - Absolutely positioned for global centering */}
            <div className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2">
                <div className="flex bg-muted rounded-lg p-1">
                    <Button
                        variant={activeTab === "Editor" ? "default" : "ghost"}
                        size="sm"
                        onClick={() => setActiveTab("Editor")}
                        className={cn(
                            "px-6 py-2",
                            activeTab === "Editor"
                                ? "bg-background shadow-sm text-foreground"
                                : "text-muted-foreground hover:text-foreground",
                        )}
                    >
                        Editor
                    </Button>
                    <Button
                        variant={activeTab === "Chat" ? "default" : "ghost"}
                        size="sm"
                        onClick={() => setActiveTab("Chat")}
                        className={cn(
                            "px-6 py-2",
                            activeTab === "Chat"
                                ? "bg-background shadow-sm text-foreground"
                                : "text-muted-foreground hover:text-foreground",
                        )}
                    >
                        Chat
                    </Button>
                    <Button
                        variant={activeTab === "Graph" ? "default" : "ghost"}
                        size="sm"
                        onClick={() => setActiveTab("Graph")}
                        className={cn(
                            "px-6 py-2",
                            activeTab === "Graph"
                                ? "bg-background shadow-sm text-foreground"
                                : "text-muted-foreground hover:text-foreground",
                        )}
                    >
                        Graph
                    </Button>
                </div>
            </div>
        </header>
    )
}
