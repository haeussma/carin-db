import { create } from "zustand"
import type { GraphSheetModel, SheetNode, PropertyValue, Project } from "@/lib/types"
import { validateModel, computeProgress } from "@/lib/validation"
import { sheetModelApi, ApiError } from "@/lib/api"

interface SchemaState {
  // Project management
  projects: Project[]
  currentProjectId: string | null
  isLoading: boolean
  isSyncing: boolean
  lastSyncError: string | null

  // Current project state
  selected: { type: "node" | "edge" | null; id?: string; propertyName?: string }
  issues: Array<{ kind: string; message: string; node?: string; prop?: string; edgeId?: string }>
  progress: number

  // Project CRUD
  createProject: (name?: string) => Promise<string>
  deleteProject: (projectId: string) => Promise<void>
  selectProject: (projectId: string) => Promise<void>
  renameProject: (projectId: string, newName: string) => Promise<void>

  // Backend sync
  syncWithBackend: () => Promise<void>
  loadFromBackend: () => Promise<void>
  saveToBackend: (model?: GraphSheetModel) => Promise<void>

  // Sheet CRUD operations (updated for new structure)
  addSheet: (name?: string, position?: { x: number; y: number }) => string
  deleteSheet: (name: string) => void
  renameSheet: (oldName: string, newName: string) => void
  setUniqueProperty: (sheetName: string, propName: string | null) => void
  updateSheetPosition: (sheetName: string, position: { x: number; y: number }) => void

  // Property CRUD operations (updated for new structure)
  addProperty: (sheetName: string, property: PropertyValue) => void
  updateProperty: (sheetName: string, oldName: string, property: PropertyValue) => void
  removeProperty: (sheetName: string, propName: string) => void

  // Graph actions
  createOrUpdateRef: (sourceSheet: string, sourceProp: string, targetSheet: string, targetProp?: string, customEdgeName?: string) => void
  replaceSheetConnection: (sourceSheet: string, sourceProp: string, targetSheet: string, targetProp?: string, customEdgeName?: string) => void
  selectNode: (nodeId: string, propertyName?: string) => void
  selectEdge: (edgeId: string) => void
  clearSelection: () => void
  updateEdge: (edgeId: string, patch: Partial<PropertyValue & { kind: "ref" }>) => void
  deleteEdge: (edgeId: string) => void

  // Validation
  recomputeIssues: () => void

  // Import/Export
  importJson: (json: any) => void
  exportJson: () => string
  loadFromSpreadsheet: (sheets: Record<string, string[]>) => void


  // Getters
  getCurrentProject: () => Project | null
  getCurrentModel: () => GraphSheetModel | null
}


const createInitialModel = (projectName: string): GraphSheetModel => ({
  project_name: projectName,
  version: 1,
  created_at: new Date().toISOString(),
  sheets: [
    {
      name: "Measurement",
      unique_property: "id",
      properties: [
        { kind: "value", name: "id", dtype: "str", unique: true },
        { kind: "value", name: "value", dtype: "float", unique: false },
        { kind: "value", name: "timestamp", dtype: "timestamp", unique: false },
      ],
      position: { x: 200, y: 150 }
    },
  ],
})

// Create default project
const defaultProject = {
  id: "example-project",
  name: "Example",
  model: createInitialModel("Example"),
  last_modified: new Date().toISOString()
}

export const useSchemaStore = create<SchemaState>()((set, get) => ({
  projects: [defaultProject],
  currentProjectId: "example-project",
  isLoading: false,  // Start ready with default project
  isSyncing: false,
  lastSyncError: null,
  selected: { type: null },
  issues: [],
  progress: 0,

  createProject: async (name) => {
    try {
      const projectName = name || `Project ${get().projects.length + 1}`
      const projectId = `project-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      const newProject: Project = {
        id: projectId,
        name: projectName,
        model: createInitialModel(projectName),
        last_modified: new Date().toISOString(),
      }

      set((state) => ({
        projects: [...state.projects, newProject],
        currentProjectId: projectId,
      }))

      // Save to backend
      await get().saveToBackend(newProject.model)

      // Ensure recomputeIssues is called after state is updated
      setTimeout(() => get().recomputeIssues(), 0)
      return projectId
    } catch (error) {
      console.error("Failed to create project:", error)
      set({ lastSyncError: error instanceof Error ? error.message : 'Failed to create project' })
      return ""
    }
  },

  deleteProject: async (projectId) => {
    const state = get()
    const wasCurrentProject = state.currentProjectId === projectId

    set((state) => ({
      projects: state.projects.filter((p) => p.id !== projectId),
      currentProjectId:
        state.currentProjectId === projectId
          ? state.projects.length > 1
            ? state.projects.find((p) => p.id !== projectId)?.id || null
            : null
          : state.currentProjectId,
    }))

    // If we deleted the current project, sync the new current project to backend
    if (wasCurrentProject) {
      const newActiveProject = get().getCurrentProject()
      if (newActiveProject) {
        await get().saveToBackend(newActiveProject.model)
      } else {
        // No projects left, clear backend
        try {
          await sheetModelApi.delete()
        } catch (error) {
          // Ignore 404 errors when deleting
          if (!(error instanceof ApiError && error.status === 404)) {
            console.error("Failed to clear backend:", error)
          }
        }
      }
    }
  },

  selectProject: async (projectId) => {
    set({ currentProjectId: projectId, selected: { type: null } })

    // Sync the selected project with backend
    const activeProject = get().getCurrentProject()
    if (activeProject) {
      await get().saveToBackend(activeProject.model)
    }

    get().recomputeIssues()
  },

  renameProject: async (projectId, newName) => {
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === projectId
          ? {
            ...p,
            name: newName,
            model: { ...p.model, project_name: newName },
            last_modified: new Date().toISOString(),
          }
          : p,
      ),
    }))

    // If this is the current project, sync to backend
    if (get().currentProjectId === projectId) {
      const activeProject = get().getCurrentProject()
      if (activeProject) {
        await get().saveToBackend(activeProject.model)
      }
    }
  },

  addSheet: (name, position) => {
    const activeProject = get().getCurrentProject()
    if (!activeProject) return ""

    const existingSheets = activeProject.model.sheets.map((s) => s.name)
    let sheetName = name
    if (!sheetName) {
      let counter = 1
      do {
        sheetName = `Sheet${counter}`
        counter++
      } while (existingSheets.includes(sheetName))
    }

    const newSheet: SheetNode = {
      name: sheetName,
      unique_property: null,
      properties: [{ kind: "value", name: "id", dtype: "str", unique: true }],
      position: position,
    }

    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === state.currentProjectId
          ? {
            ...p,
            model: { ...p.model, sheets: [...p.model.sheets, newSheet] },
            last_modified: new Date().toISOString(),
          }
          : p,
      ),
    }))
    get().recomputeIssues()

    // Auto-sync with backend if this is the current project
    const currentProj = get().getCurrentProject()
    if (currentProj) {
      get().saveToBackend(currentProj.model).catch(console.error)
    }

    return sheetName
  },

  deleteSheet: (name) => {
    const activeProject = get().getCurrentProject()
    if (!activeProject) return

    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === state.currentProjectId
          ? {
            ...p,
            model: {
              ...p.model,
              sheets: p.model.sheets
                .filter((s) => s.name !== name)
                .map((sheet) => ({
                  ...sheet,
                  properties: (sheet.properties || []).filter((prop) => prop.kind !== "ref" || prop.to !== name),
                })),
            },
            last_modified: new Date().toISOString(),
          }
          : p,
      ),
      selected: state.selected.id === name ? { type: null } : state.selected,
    }))
    get().recomputeIssues()

    // Auto-sync with backend if this is the current project
    const currentProj = get().getCurrentProject()
    if (currentProj) {
      get().saveToBackend(currentProj.model).catch(console.error)
    }
  },

  renameSheet: (oldName, newName) => {
    const activeProject = get().getCurrentProject()
    if (!activeProject) return

    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === state.currentProjectId
          ? {
            ...p,
            model: {
              ...p.model,
              sheets: p.model.sheets.map((sheet) => ({
                ...sheet,
                name: sheet.name === oldName ? newName : sheet.name,
                properties: (sheet.properties || []).map((prop) =>
                  prop.kind === "ref" && prop.to === oldName ? { ...prop, to: newName } : prop,
                ),
              })),
            },
            last_modified: new Date().toISOString(),
          }
          : p,
      ),
      selected: state.selected.id === oldName ? { ...state.selected, id: newName } : state.selected,
    }))
    get().recomputeIssues()

    // Auto-sync with backend if this is the current project
    const currentProj = get().getCurrentProject()
    if (currentProj) {
      get().saveToBackend(currentProj.model).catch(console.error)
    }
  },

  setUniqueProperty: (sheetName, propName) => {
    const activeProject = get().getCurrentProject()
    if (!activeProject) return

    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === state.currentProjectId
          ? {
            ...p,
            model: {
              ...p.model,
              sheets: p.model.sheets.map((sheet) =>
                sheet.name === sheetName ? { ...sheet, unique_property: propName } : sheet,
              ),
            },
            last_modified: new Date().toISOString(),
          }
          : p,
      ),
    }))
    get().recomputeIssues()

    // Auto-sync with backend if this is the current project
    const currentProj = get().getCurrentProject()
    if (currentProj) {
      get().saveToBackend(currentProj.model).catch(console.error)
    }
  },

  updateSheetPosition: (sheetName, position) => {
    const activeProject = get().getCurrentProject()
    if (!activeProject) return

    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === state.currentProjectId
          ? {
            ...p,
            model: {
              ...p.model,
              sheets: p.model.sheets.map((sheet) =>
                sheet.name === sheetName ? { ...sheet, position } : sheet,
              ),
            },
            last_modified: new Date().toISOString(),
          }
          : p,
      ),
    }))

    // Auto-sync with backend if this is the current project
    const currentProj = get().getCurrentProject()
    if (currentProj) {
      get().saveToBackend(currentProj.model).catch(console.error)
    }
  },

  addProperty: (sheetName, property) => {
    const activeProject = get().getCurrentProject()
    if (!activeProject) return

    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === state.currentProjectId
          ? {
            ...p,
            model: {
              ...p.model,
              sheets: p.model.sheets.map((sheet) =>
                sheet.name === sheetName ? { ...sheet, properties: [...sheet.properties, property] } : sheet,
              ),
            },
            last_modified: new Date().toISOString(),
          }
          : p,
      ),
    }))
    get().recomputeIssues()

    // Auto-sync with backend if this is the current project
    const currentProj = get().getCurrentProject()
    if (currentProj) {
      get().saveToBackend(currentProj.model).catch(console.error)
    }
  },

  updateProperty: (sheetName, oldName, property) => {
    const activeProject = get().getCurrentProject()
    if (!activeProject) return


    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === state.currentProjectId
          ? {
            ...p,
            model: {
              ...p.model,
              sheets: p.model.sheets.map((sheet) => {
                if (sheet.name === sheetName) {
                  // Update the property in the target sheet
                  return {
                    ...sheet,
                    properties: (sheet.properties || []).map((prop) => (prop.name === oldName ? property : prop)),
                  }
                } else {
                  // Update any references in other sheets that point to the renamed property
                  return {
                    ...sheet,
                    properties: (sheet.properties || []).map((prop) => {
                      if (prop.kind === 'ref' && prop.to === sheetName && prop.on === oldName) {
                        return {
                          ...prop,
                          on: property.name, // Update the target property name
                        }
                      }
                      return prop
                    }),
                  }
                }
              }),
            },
            last_modified: new Date().toISOString(),
          }
          : p,
      ),
    }))
    get().recomputeIssues()

    // Auto-sync with backend if this is the current project
    const currentProj = get().getCurrentProject()
    if (currentProj) {
      get().saveToBackend(currentProj.model).catch(console.error)
    }
  },

  removeProperty: (sheetName, propName) => {
    const activeProject = get().getCurrentProject()
    if (!activeProject) return

    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === state.currentProjectId
          ? {
            ...p,
            model: {
              ...p.model,
              sheets: p.model.sheets.map((sheet) =>
                sheet.name === sheetName
                  ? {
                    ...sheet,
                    properties: (sheet.properties || []).filter((prop) => prop.name !== propName),
                    unique_property: sheet.unique_property === propName ? null : sheet.unique_property,
                  }
                  : sheet,
              ),
            },
            last_modified: new Date().toISOString(),
          }
          : p,
      ),
    }))
    get().recomputeIssues()

    // Auto-sync with backend if this is the current project
    const currentProj = get().getCurrentProject()
    if (currentProj) {
      get().saveToBackend(currentProj.model).catch(console.error)
    }
  },

  createOrUpdateRef: (sourceSheet, sourceProp, targetSheet, targetProp, customEdgeName) => {
    const currentModel = get().getCurrentModel()
    if (!currentModel) return

    const targetSheetConfig = currentModel.sheets.find((s) => s.name === targetSheet)

    // Use provided targetProp or fall back to the sheet's unique_property
    const targetProperty = targetProp || targetSheetConfig?.unique_property

    if (!targetProperty) return

    // Use custom edge name if provided, otherwise use consistent HAS_ format
    const edgeName = customEdgeName || `HAS_${sourceProp.toUpperCase()}`

    const refProperty: PropertyValue = {
      kind: "ref",
      name: sourceProp,
      to: targetSheet,
      on: targetProperty,
      edge: edgeName,
      multi: { sep: ",", trim: true, allow_empty: false },
      case: "insensitive",
      on_miss: "error",
      unique: false,
    }

    get().updateProperty(sourceSheet, sourceProp, refProperty)
  },

  replaceSheetConnection: (sourceSheet, sourceProp, targetSheet, targetProp, customEdgeName) => {
    const currentModel = get().getCurrentModel()
    if (!currentModel) return

    const targetSheetConfig = currentModel.sheets.find((s) => s.name === targetSheet)

    // Use provided targetProp or fall back to the sheet's unique_property
    const targetProperty = targetProp || targetSheetConfig?.unique_property

    if (!targetProperty) return

    // Use custom edge name if provided, otherwise use consistent HAS_ format
    const edgeName = customEdgeName || `HAS_${sourceProp.toUpperCase()}`

    const refProperty: PropertyValue = {
      kind: "ref",
      name: sourceProp,
      to: targetSheet,
      on: targetProperty,
      edge: edgeName,
      multi: { sep: ",", trim: true, allow_empty: false },
      case: "insensitive",
      on_miss: "error",
      unique: false,
    }

    // Atomic operation: replace all refs to the target sheet with the new one
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === state.currentProjectId
          ? {
            ...p,
            model: {
              ...p.model,
              sheets: p.model.sheets.map((sheet) => {
                if (sheet.name === sourceSheet) {
                  return {
                    ...sheet,
                    properties: [
                      // Keep all non-ref properties and refs to other sheets
                      ...sheet.properties.filter(prop =>
                        prop.kind !== "ref" || prop.to !== targetSheet
                      ),
                      // Add the new ref property
                      refProperty
                    ],
                  }
                }
                return sheet
              }),
            },
            last_modified: new Date().toISOString(),
          }
          : p,
      ),
    }))

    get().recomputeIssues()

    // Auto-sync with backend if this is the current project
    const currentProj = get().getCurrentProject()
    if (currentProj) {
      get().saveToBackend(currentProj.model).catch(console.error)
    }
  },

  selectNode: (nodeId, propertyName) => {
    set({ selected: { type: "node", id: nodeId, propertyName } })
  },

  selectEdge: (edgeId) => {
    set({ selected: { type: "edge", id: edgeId } })
  },

  clearSelection: () => {
    set({ selected: { type: null } })
  },

  updateEdge: (edgeId, patch) => {
    const [sourceSheet, sourceProp] = edgeId.split(".")
    const currentModel = get().getCurrentModel()
    if (!currentModel) return

    const sourceSheetConfig = currentModel.sheets.find((s) => s.name === sourceSheet)
    const currentProp = (sourceSheetConfig?.properties || []).find((p) => p.name === sourceProp)

    if (currentProp && currentProp.kind === "ref") {
      get().updateProperty(sourceSheet, sourceProp, { ...currentProp, ...patch })
    }
  },

  deleteEdge: (edgeId) => {
    const [sourceSheet, sourceProp] = edgeId.split(".")
    get().removeProperty(sourceSheet, sourceProp)
  },

  recomputeIssues: () => {
    const currentModel = get().getCurrentModel()
    if (!currentModel) {
      set({ issues: [], progress: 0 })
      return
    }

    const issues = validateModel(currentModel)
    const progress = computeProgress(currentModel, issues)
    set({ issues, progress })
  },

  importJson: (json) => {
    try {
      const activeProject = get().getCurrentProject()
      if (!activeProject) return

      set((state) => ({
        projects: state.projects.map((p) =>
          p.id === state.currentProjectId ? { ...p, model: json, last_modified: new Date().toISOString() } : p,
        ),
      }))
      get().recomputeIssues()
    } catch (error) {
      console.error("Failed to import JSON:", error)
    }
  },

  exportJson: () => {
    const currentModel = get().getCurrentModel()
    return currentModel ? JSON.stringify(currentModel, null, 2) : "{}"
  },

  loadFromSpreadsheet: (sheets) => {
    const activeProject = get().getCurrentProject()
    if (!activeProject) return

    const newSheets: SheetNode[] = []

    Object.entries(sheets).forEach(([sheetName, columns]) => {
      const properties: PropertyValue[] = columns.map((col, index) => ({
        kind: "value" as const,
        name: col,
        dtype: "str" as const,
        unique: index === 0, // First column is unique by default
      }))

      newSheets.push({
        name: sheetName,
        unique_property: columns[0] || null,
        properties,
      })
    })

    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === state.currentProjectId
          ? {
            ...p,
            model: { ...p.model, sheets: newSheets },
            last_modified: new Date().toISOString(),
          }
          : p,
      ),
    }))
    get().recomputeIssues()

    // Auto-sync with backend if this is the current project
    const currentProj = get().getCurrentProject()
    if (currentProj) {
      get().saveToBackend(currentProj.model).catch(console.error)
    }
  },


  getCurrentProject: () => {
    const { projects, currentProjectId } = get()
    return projects.find((p) => p.id === currentProjectId) || null
  },

  getCurrentModel: () => {
    const activeProject = get().getCurrentProject()
    return activeProject?.model || null
  },

  // Backend sync functions
  syncWithBackend: async () => {
    set({ isSyncing: true, lastSyncError: null })
    try {
      await get().loadFromBackend()
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Sync failed'
      set({ lastSyncError: errorMessage })
      console.error("Failed to sync with backend:", error)
    } finally {
      set({ isSyncing: false })
    }
  },

  loadFromBackend: async () => {
    set({ isLoading: true, lastSyncError: null })
    try {
      const backendModel = await sheetModelApi.get()

      // Find existing project with this model or create new one
      const state = get()
      let existingProject = state.projects.find(p =>
        p.model.project_name === backendModel.project_name
      )

      if (existingProject) {
        // Update existing project with backend data
        set((state) => ({
          projects: state.projects.map(p =>
            p.id === existingProject!.id
              ? { ...p, model: backendModel, last_modified: new Date().toISOString() }
              : p
          ),
          currentProjectId: existingProject.id,
        }))
      } else {
        // Create new project from backend model
        const projectId = `project-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        const newProject: Project = {
          id: projectId,
          name: backendModel.project_name,
          model: backendModel,
          last_modified: new Date().toISOString(),
        }

        set((state) => ({
          projects: [...state.projects, newProject],
          currentProjectId: projectId,
        }))
      }

      get().recomputeIssues()
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        // Backend empty → create a local sample
        console.log("No backend model found, creating default project")
        const sample = createInitialModel("Example")
        const projectId = `project-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
        set((state) => ({
          projects: [...state.projects, { id: projectId, name: "Example", model: sample, last_modified: new Date().toISOString() }],
          currentProjectId: projectId,
        }))
        get().recomputeIssues()
        // Optional: persist to backend
        get().saveToBackend(sample).catch(() => { })
        return
      } else {
        const errorMessage = error instanceof Error ? error.message : 'Failed to load from backend'
        set({ lastSyncError: errorMessage })
        console.error("Failed to load from backend:", error)
      }
    } finally {
      set({ isLoading: false })
    }
  },

  saveToBackend: async (model?: GraphSheetModel) => {
    set({ isSyncing: true, lastSyncError: null })
    try {
      const modelToSave = model || get().getCurrentModel()
      if (modelToSave) {
        await sheetModelApi.save(modelToSave)

        // Update last_modified timestamp for current project
        const currentProjectId = get().currentProjectId
        if (currentProjectId) {
          set((state) => ({
            projects: state.projects.map(p =>
              p.id === currentProjectId
                ? { ...p, last_modified: new Date().toISOString() }
                : p
            ),
          }))
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save to backend'
      set({ lastSyncError: errorMessage })
      console.warn("Backend save failed, continuing with local changes:", error)
      // Don't re-throw the error - allow the app to continue working locally
      // The user will see the error message but can still use the app
    } finally {
      set({ isSyncing: false })
    }
  },
}))
