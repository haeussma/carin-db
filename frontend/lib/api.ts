import type { GraphSheetModel } from "./types"

const API_BASE = "/api"

export class ApiError extends Error {
    constructor(public status: number, message: string) {
        super(message || `HTTP ${status}`)
        this.name = "ApiError"
    }
}

function withJsonHeaders(init: RequestInit | undefined) {
    const isForm = init?.body instanceof FormData
    const headers = new Headers(init?.headers)
    if (!headers.has("Accept")) headers.set("Accept", "application/json")
    if (!isForm && init?.body && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json")
    }
    return { ...init, headers }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
    const res = await fetch(url, withJsonHeaders(init))

    if (!res.ok) {
        // Best-effort error text
        let msg = res.statusText
        try {
            const ct = res.headers.get("content-type") || ""
            msg = ct.includes("application/json") ? JSON.stringify(await res.json()) : await res.text()
        } catch { }
        throw new ApiError(res.status, msg)
    }

    if (res.status === 204) {
        // Endpoint deliberately returned no content (DELETE, some POSTs)
        return undefined as unknown as T
    }

    // Prefer JSON, but allow text (e.g., status endpoints)
    const ct = res.headers.get("content-type") || ""
    if (ct.includes("application/json")) return (await res.json()) as T
    return (await res.text()) as unknown as T
}

// Tiny verb helpers so call sites stay clean
const get = <T>(path: string) => request<T>(`${API_BASE}${path}`)
const postJson = <T>(path: string, body: unknown) =>
    request<T>(`${API_BASE}${path}`, { method: "POST", body: JSON.stringify(body) })
const del = (path: string) => request<void>(`${API_BASE}${path}`, { method: "DELETE" })
const postForm = <T>(path: string, fd: FormData) =>
    request<T>(`${API_BASE}${path}`, { method: "POST", body: fd })

const enc = encodeURIComponent
const projPath = (name: string) => `/projects/${enc(name)}`

export const projectsApi = {
    /** GET /projects/load -> GraphSheetModel[] */
    loadAll(): Promise<GraphSheetModel[]> {
        console.log('🔍 API: Loading all projects')
        return get<GraphSheetModel[]>("/projects/load")
    },

    /** GET /projects/{project_name} -> GraphSheetModel */
    getOne(projectName: string): Promise<GraphSheetModel> {
        return get<GraphSheetModel>(projPath(projectName))
    },

    /** POST /projects/{project_name} (body: GraphSheetModel) -> void */
    save(project: GraphSheetModel): Promise<void> {
        console.log('🔍 API: Saving project:', project.project_name, project)
        // Backend returns None (204), so we don't expect a response
        return postJson<void>(projPath(project.project_name), project)
    },

    /** DELETE /projects/{project_name} -> 204 No Content */
    remove(projectName: string): Promise<void> {
        // Treat as void; do NOT expect JSON
        return del(projPath(projectName))
    },

    /** POST /spreadsheet/upload-schema?project_name=... (multipart) -> 204 */
    async importSchema(file: File, projectName: string): Promise<void> {
        const fd = new FormData()
        fd.append("file", file)
        const qs = new URLSearchParams({ project_name: projectName }).toString()
        await postForm<void>(`/spreadsheet/upload-schema?${qs}`, fd)
    },
}

export const databaseApi = {
    getStatus(): Promise<any> {
        return get("/database/status")
    },
    getStructure(): Promise<any> {
        return get("/database/db_structure")
    },
    deleteAll(): Promise<void> {
        return del("/database/delete_all")
    },
}
