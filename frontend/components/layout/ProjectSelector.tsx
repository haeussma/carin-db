"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useSchemaStore } from "@/store/useSchemaStore"
import { Plus, FolderOpen } from "lucide-react"

export function ProjectSelector() {
  const { projects, currentProjectId, isLoading, selectProject, createProject } = useSchemaStore()
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [newProjectName, setNewProjectName] = useState("")

  const currentProject = projects.find((p) => p.id === currentProjectId)



  const handleCreateProject = async () => {
    if (newProjectName.trim()) {
      try {
        const projectId = await createProject(newProjectName.trim())
        setNewProjectName("")
        setIsCreateDialogOpen(false)
      } catch (error) {
        console.error('❌ Failed to create project:', error)
        // Still close the dialog even if backend save fails
        setNewProjectName("")
        setIsCreateDialogOpen(false)
      }
    }
  }

  return (
    <div className="flex items-center gap-2">
      <FolderOpen className="h-4 w-4 text-muted-foreground" />
      <Select value={currentProjectId || ""} onValueChange={selectProject} disabled={isLoading}>
        <SelectTrigger className="w-48">
          <SelectValue placeholder={isLoading ? "Loading..." : "Select project"}>
            {isLoading ? "Loading..." : currentProject?.name || "No project available"}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {projects.map((project) => (
            <SelectItem key={project.id} value={project.id}>
              {project.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm">
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
                placeholder="Enter project name"
                onKeyDown={(e) => e.key === "Enter" && handleCreateProject()}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateProject} disabled={!newProjectName.trim()}>
                Create Project
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
