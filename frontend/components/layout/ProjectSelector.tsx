"use client"

import React from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useSchemaStore } from "@/store/useSchemaStore"
import { Plus, FolderOpen, RefreshCw } from "lucide-react"

export function ProjectSelector() {
  const {
    projects,
    currentProjectName,
    isLoading,
    selectProject,
    createProject,
    loadFromBackend,
  } = useSchemaStore()

  const [isCreateDialogOpen, setIsCreateDialogOpen] = React.useState(false)
  const [newProjectName, setNewProjectName] = React.useState("")

  // Load project list (and first project) on mount
  React.useEffect(() => {
    void loadFromBackend()
  }, [loadFromBackend])

  const handleCreateProject = async () => {
    const name = newProjectName.trim()
    if (!name) return
    try {
      const projectName = await createProject(name)
      if (projectName) {
        console.log("✅ Created project:", projectName)
        // Project is automatically selected in createProject
      } else {
        console.error("❌ Failed to create project")
      }
    } catch (error) {
      console.error("❌ Error creating project:", error)
    } finally {
      setNewProjectName("")
      setIsCreateDialogOpen(false)
    }
  }

  const disabled = isLoading || projects.length === 0

  return (
    <div className="flex items-center gap-2">
      <FolderOpen className="h-4 w-4 text-muted-foreground" />

      <Select
        value={currentProjectName ?? ""}
        onValueChange={(name) => void selectProject(name)}
        disabled={isLoading || projects.length === 0}
      >
        <SelectTrigger className="w-56">
          <SelectValue placeholder={isLoading ? "Loading..." : "Select project"} />
        </SelectTrigger>
        <SelectContent>
          {projects.length === 0 ? (
            <div className="px-2 py-1.5 text-sm text-muted-foreground">No projects found</div>
          ) : (
            projects.map((project) => (
              <SelectItem key={project.name} value={project.name}>
                {project.name}
              </SelectItem>
            ))
          )}
        </SelectContent>
      </Select>

      <Button
        variant="ghost"
        size="icon"
        className="h-9 w-9"
        title="Refresh projects"
        onClick={() => void loadFromBackend()}
        disabled={isLoading}
      >
        <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
      </Button>

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm" title="Create project">
            <Plus className="h-4 w-4" />
          </Button>
        </DialogTrigger>

        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Project</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="project-name">Project Name</Label>
              <Input
                id="project-name"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="New project"
                onKeyDown={(e) => e.key === "Enter" && handleCreateProject()}
                autoFocus
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateProject} disabled={!newProjectName.trim()}>
                Create
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
