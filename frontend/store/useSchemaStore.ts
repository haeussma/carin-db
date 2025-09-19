import { create } from "zustand"
import type { GraphSheetModel, SheetNode, PropertyValue } from "@/lib/types"
import { validateModel, computeProgress } from "@/lib/validation"
import { ApiError, projectsApi } from "@/lib/api"

interface SchemaState {
  // Project management
  projects: GraphSheetModel[]
  currentProjectName: string
  isLoading: boolean
  isSyncing: boolean,
  lastSyncError: string | null

  // UI State
  activeTab: "Editor" | "Chat" | "Graph"
  setActiveTab: (tab: "Editor" | "Chat" | "Graph") => void

  // Current project state
  selected: { type: "node" | "edge" | null; id?: string; propertyName?: string }
  issues: Array<{ kind: string; message: string; node?: string; prop?: string; edgeId?: string }>
  progress: number

  // Project CRUD
  createProject: (name: string) => Promise<string>
  deleteProject: (projectName: string) => Promise<void>
  selectProject: (projectName: string) => Promise<void>
  renameProject: (projectName: string, newName: string) => Promise<void>

  // Backend sync
  syncWithBackend: () => Promise<void>
  loadFromBackend: () => Promise<void>
  saveToBackend: (projectName?: string) => Promise<void>

  // Sheet CRUD
  addSheet: (name?: string, position?: { x: number; y: number }) => string
  deleteSheet: (name: string) => void
  renameSheet: (oldName: string, newName: string) => void
  updateSheetPosition: (sheetName: string, position: { x: number; y: number }) => void

  // Property CRUD
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
  importSchema: (file: File, projectName?: string) => Promise<void>

  // Getters
  getCurrentProject: () => GraphSheetModel  // Always returns a project
}

const createInitialModel = (projectName: string): GraphSheetModel => ({
  project_name: projectName,
  created_at: new Date().toISOString(),
  last_modified: new Date().toISOString(),
  sheets: [
    {
      name: "Measurement",
      properties: [
        { kind: "value", name: "id", dtype: "str", unique: true },
        { kind: "value", name: "value", dtype: "float", unique: false },
        { kind: "value", name: "timestamp", dtype: "timestamp", unique: false },
      ],
      position: { x: 200, y: 150 }
    },
  ],
})

export const useSchemaStore = create<SchemaState>()((set, get) => {
  // ---- helpers -------------------------------------------------------------

  const setError = (err: unknown, fallback: string) => {
    const msg = err instanceof ApiError || err instanceof Error ? err.message : fallback
    set({ lastSyncError: msg })
    console.error(fallback, err)
  }

  const getCurrentProject = (): GraphSheetModel => {
    const { projects, currentProjectName } = get()
    const project = projects.find(p => p.project_name === currentProjectName)
    if (!project) {
      throw new Error(`Current project '${currentProjectName}' not found in projects list`)
    }
    console.log('🔍 getCurrentProject:', { currentProjectName, projectsCount: projects.length, found: true })
    return project
  }


  const getUniqueProperties = (sheet: SheetNode): string[] => {
    return sheet.properties.filter(prop => prop.unique).map(prop => prop.name)
  }

  const touch = (p: GraphSheetModel) => ({ ...p, last_modified: new Date().toISOString() })

  /** mutate current project immutably, recompute issues, and save */
  const updateCurrent = (mutator: (p: GraphSheetModel) => GraphSheetModel) => {
    const current = getCurrentProject() // Always exists now
    set(s => ({
      projects: s.projects.map(p => (p.project_name === current.project_name ? touch(mutator(p)) : p)),
    }))
    get().recomputeIssues()
    // best effort save (no await here so UI stays snappy)
    void get().saveToBackend(current.project_name)
  }

  // ---- store ---------------------------------------------------------------

  return {
    projects: [],
    currentProjectName: 'new', // Always has a value
    isLoading: true,
    isSyncing: false,
    lastSyncError: null,

    // UI State
    activeTab: "Editor" as "Editor" | "Chat" | "Graph",
    setActiveTab: (tab) => set({ activeTab: tab }),

    selected: { type: null },
    issues: [],
    progress: 0,

    // -------- Project CRUD --------

    createProject: async (name: string) => {
      try {
        const baseName = name.trim()
        const { projects } = get()

        // Ensure unique project name
        let projectName = baseName
        let counter = 1
        while (projects.some(p => p.project_name === projectName)) {
          projectName = `${baseName}_${counter}`
          counter++
        }

        const project: GraphSheetModel = createInitialModel(projectName)

        set(s => ({
          projects: [...s.projects, project],
          currentProjectName: project.project_name,
        }))
        get().recomputeIssues()

        await projectsApi.save(project)
        return project.project_name
      } catch (e) {
        setError(e, "Failed to create project")
        return ""
      }
    },

    deleteProject: async (projectName) => {
      const proj = get().projects.find(p => p.project_name === projectName)
      if (!proj) {
        set(s => ({ projects: s.projects.filter(p => p.project_name !== projectName) }))
        return
      }
      try {
        await projectsApi.remove(proj.project_name)
      } catch (e) {
        // keep going even if backend delete fails
        console.warn("Backend delete failed:", e)
      }
      set(s => {
        const remaining = s.projects.filter(p => p.project_name !== projectName)
        // Always ensure a project is selected
        let newCurrentProjectName: string
        if (s.currentProjectName === projectName) {
          if (remaining.length > 0) {
            newCurrentProjectName = remaining[0].project_name
          } else {
            // If no projects remain, reload from backend to get/create default
            void get().loadFromBackend()
            return s // Don't update state, let loadFromBackend handle it
          }
        } else {
          newCurrentProjectName = s.currentProjectName
        }
        return {
          projects: remaining,
          currentProjectName: newCurrentProjectName,
        }
      })
      get().recomputeIssues()
    },

    selectProject: async (projectName) => {
      set({ currentProjectName: projectName, selected: { type: null } })
      get().recomputeIssues()
    },

    renameProject: async (projectName, newName) => {
      const proj = get().projects.find(p => p.project_name === projectName)
      if (!proj) return
      const oldName = proj.project_name
      const updated: GraphSheetModel = {
        ...proj,
        project_name: newName,
        last_modified: new Date().toISOString(),
      }

      // optimistic local update
      set(s => ({
        projects: s.projects.map(p => (p.project_name === projectName ? updated : p)),
        currentProjectName: s.currentProjectName === projectName ? updated.project_name : s.currentProjectName,
      }))
      get().recomputeIssues()

      try {
        await projectsApi.save(updated)
        if (oldName !== newName) {
          try { await projectsApi.remove(oldName) } catch { }
        }
      } catch (e) {
        setError(e, "Rename failed")
      }
    },

    // -------- Backend sync --------

    syncWithBackend: async () => {
      set({ isSyncing: true, lastSyncError: null })
      try {
        await get().loadFromBackend()
      } finally {
        set({ isSyncing: false })
      }
    },

    loadFromBackend: async () => {
      set({ isLoading: true, lastSyncError: null })
      try {
        console.log("😎 Loading projects from backend")
        const projects = await projectsApi.loadAll()

        const { currentProjectName } = get()

        if (projects.length === 0) {
          // No projects exist - raise error
          throw new Error("No projects found in backend. Please create a project first.")
        } else {
          // Projects exist - ensure one is always selected
          let selectedProject: string

          if (projects.find(p => p.project_name === currentProjectName)) {
            // Current selection is still valid
            selectedProject = currentProjectName
          } else {
            // Select most recently modified project
            const mostRecent = projects.reduce((a, b) =>
              new Date(a.last_modified) > new Date(b.last_modified) ? a : b
            );
            selectedProject = mostRecent.project_name
          }

          set({ projects, currentProjectName: selectedProject });
          console.log("✅ Auto-selected project:", selectedProject)
        }
        get().recomputeIssues()
      } catch (e) {
        console.error("😡 Failed to load projects from backend", e)
        setError(e, "Failed to load from backend")

        // No fallback - let the error propagate
        console.log("⚠️ Backend error - no fallback project created")
      } finally {
        set({ isLoading: false })
        console.log("😎 Loaded projects from backend")
      }
    },

    saveToBackend: async (projectName?: string) => {
      set({ isSyncing: true, lastSyncError: null })
      try {
        const project = projectName
          ? get().projects.find(p => p.project_name === projectName)
          : getCurrentProject() // Always exists now

        if (!project) {
          console.warn('Project not found for save:', projectName)
          return
        }

        const toSave: GraphSheetModel = { ...project, last_modified: new Date().toISOString() }
        await projectsApi.save(toSave)

        // Update the project in the store with the new timestamp
        set(s => ({
          projects: s.projects.map(p => (p.project_name === project.project_name ? toSave : p)),
        }))
      } catch (e) {
        setError(e, "Failed to save to backend")
      } finally {
        set({ isSyncing: false })
      }
    },


    // -------- Sheets --------

    addSheet: (name, position) => {
      const current = getCurrentProject() // Always exists now
      const existing = new Set(current.sheets.map(s => s.name))
      let sheetName = name
      if (!sheetName) {
        let i = 1
        while (existing.has(`Sheet${i}`)) i++
        sheetName = `Sheet${i}`
      }

      // Ensure unique name even if provided name conflicts
      let uniqueName = sheetName
      let counter = 1
      while (existing.has(uniqueName)) {
        uniqueName = `${sheetName}_${counter}`
        counter++
      }

      const newSheet: SheetNode = {
        name: uniqueName,
        properties: [{ kind: "value", name: "id", dtype: "str", unique: true }],
        position,
      }
      updateCurrent(p => ({ ...p, sheets: [...p.sheets, newSheet] }))
      return uniqueName
    },

    deleteSheet: (name) => {
      updateCurrent(p => ({
        ...p,
        sheets: p.sheets
          .filter(s => s.name !== name)
          .map(s => ({
            ...s,
            properties: s.properties.filter(prop => prop.kind !== "ref" || prop.to !== name),
          })),
      }))
      set(s => ({ selected: s.selected.id === name ? { type: null } : s.selected }))
    },

    renameSheet: (oldName, newName) => {
      updateCurrent(p => ({
        ...p,
        sheets: p.sheets.map(sheet => ({
          ...sheet,
          name: sheet.name === oldName ? newName : sheet.name,
          properties: sheet.properties.map(prop =>
            prop.kind === "ref" && prop.to === oldName ? { ...prop, to: newName } : prop
          ),
        })),
      }))
      set(s => ({ selected: s.selected.id === oldName ? { ...s.selected, id: newName } : s.selected }))
    },


    updateSheetPosition: (sheetName, position) => {
      updateCurrent(p => ({
        ...p,
        sheets: p.sheets.map(s => (s.name === sheetName ? { ...s, position } : s)),
      }))
    },

    // -------- Properties --------

    addProperty: (sheetName, property) => {
      const current = getCurrentProject() // Always exists now
      const sheet = current.sheets.find(s => s.name === sheetName)
      if (!sheet) return

      // Check for duplicate property names
      const existingNames = sheet.properties.map(p => p.name)
      if (existingNames.includes(property.name)) {
        console.warn(`Property "${property.name}" already exists in sheet "${sheetName}"`)
        return // Don't add duplicate
      }

      updateCurrent(p => ({
        ...p,
        sheets: p.sheets.map(s => (s.name === sheetName ? { ...s, properties: [...s.properties, property] } : s)),
      }))
    },

    updateProperty: (sheetName, oldName, property) => {
      updateCurrent(p => ({
        ...p,
        sheets: p.sheets.map(sheet => {
          if (sheet.name === sheetName) {
            return {
              ...sheet,
              properties: sheet.properties.map(prop => (prop.name === oldName ? property : prop)),
            }
          }
          return {
            ...sheet,
            properties: sheet.properties.map(prop =>
              prop.kind === "ref" && prop.to === sheetName && prop.on === oldName
                ? { ...prop, on: property.name }
                : prop
            ),
          }
        }),
      }))
    },

    removeProperty: (sheetName, propName) => {
      updateCurrent(p => ({
        ...p,
        sheets: p.sheets.map(sheet =>
          sheet.name === sheetName
            ? {
              ...sheet,
              properties: sheet.properties.filter(prop => prop.name !== propName),
            }
            : sheet
        ),
      }))
    },

    // -------- Graph actions --------
    createOrUpdateRef: (sourceSheet, sourceProp, targetSheet, targetProp, customEdgeName) => {
      const model = getCurrentProject() // Always exists now
      const target = model.sheets.find(s => s.name === targetSheet)
      if (!target) return
      const uniqueProps = getUniqueProperties(target)
      const on = targetProp ?? (uniqueProps.length > 0 ? uniqueProps[0] : null)
      if (!on) return
      const edgeName = customEdgeName || `HAS_${sourceProp.toUpperCase()}`
      const ref: PropertyValue = {
        kind: "ref",
        name: sourceProp,
        to: targetSheet,
        on,
        edge: edgeName,
        multi: { sep: ",", trim: true, allow_empty: false },
        case: "insensitive",
        on_miss: "error",
        unique: false,
      }
      get().updateProperty(sourceSheet, sourceProp, ref)

      // Automatically set target property as unique
      const targetProperty = target.properties.find(p => p.name === on)
      if (targetProperty && targetProperty.kind === 'value') {
        get().updateProperty(targetSheet, on, { ...targetProperty, unique: true })
      }
    },

    replaceSheetConnection: (sourceSheet, sourceProp, targetSheet, targetProp, customEdgeName) => {
      const model = getCurrentProject() // Always exists now
      const target = model.sheets.find(s => s.name === targetSheet)
      if (!target) return
      const uniqueProps = getUniqueProperties(target)
      const on = targetProp ?? (uniqueProps.length > 0 ? uniqueProps[0] : null)
      if (!on) return
      const edgeName = customEdgeName || `HAS_${sourceProp.toUpperCase()}`
      const ref: PropertyValue = {
        kind: "ref",
        name: sourceProp,
        to: targetSheet,
        on,
        edge: edgeName,
        multi: { sep: ",", trim: true, allow_empty: false },
        case: "insensitive",
        on_miss: "error",
        unique: false,
      }
      updateCurrent(p => ({
        ...p,
        sheets: p.sheets.map(sheet =>
          sheet.name === sourceSheet
            ? {
              ...sheet,
              properties: [
                ...sheet.properties.filter(prop => !(prop.kind === "ref" && prop.to === targetSheet && prop.name === sourceProp)),
                ref,
              ],
            }
            : sheet
        ),
      }))

      // Automatically set target property as unique
      const targetProperty = target.properties.find(p => p.name === on)
      if (targetProperty && targetProperty.kind === 'value') {
        get().updateProperty(targetSheet, on, { ...targetProperty, unique: true })
      }
    },

    selectNode: (nodeId, propertyName) => set({ selected: { type: "node", id: nodeId, propertyName } }),
    selectEdge: (edgeId) => set({ selected: { type: "edge", id: edgeId } }),
    clearSelection: () => set({ selected: { type: null } }),

    updateEdge: (edgeId, patch) => {
      const [sourceSheet, sourceProp] = edgeId.split(".")
      const model = getCurrentProject() // Always exists now
      const source = model.sheets.find(s => s.name === sourceSheet)
      const curr = source?.properties.find(p => p.name === sourceProp)
      if (curr && curr.kind === "ref") {
        get().updateProperty(sourceSheet, sourceProp, { ...curr, ...patch })
      }
    },

    deleteEdge: (edgeId) => {
      const [sourceSheet, sourceProp] = edgeId.split(".")
      get().removeProperty(sourceSheet, sourceProp)
    },

    // -------- Validation / Import / Export --------

    recomputeIssues: () => {
      const model = getCurrentProject() // Always exists now
      const issues = validateModel(model)
      const progress = computeProgress(model, issues)
      set({ issues, progress })
    },

    importSchema: async (file: File, projectName?: string) => {
      try {
        const name = projectName ?? `Imported Project ${Date.now()}`;
        await projectsApi.importSchema(file, name);

        // Refresh the store to get the updated project state from backend
        await get().loadFromBackend();
        console.log('🔄 Imported schema and refreshed store state');
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'Import failed';
        set({ lastSyncError: msg });
        throw e;
      }
    },

    // getters
    getCurrentProject,
  }
})
