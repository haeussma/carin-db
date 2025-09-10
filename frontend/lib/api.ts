/**
 * API utilities for backend communication
 */

import type { GraphSheetModel } from './types'

const API_BASE = '/api'

export class ApiError extends Error {
    constructor(public status: number, message: string) {
        super(message)
        this.name = 'ApiError'
    }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options?.headers,
            },
            ...options,
        })

        if (!response.ok) {
            const errorText = await response.text().catch(() => 'Unknown error')

            // Provide more user-friendly error messages
            if (response.status === 404) {
                throw new ApiError(response.status, 'Backend service not available. Please ensure the backend server is running.')
            } else if (response.status === 500) {
                throw new ApiError(response.status, 'Server error occurred. Please try again later.')
            } else {
                throw new ApiError(response.status, errorText)
            }
        }

        return response.json()
    } catch (error) {
        if (error instanceof ApiError) {
            throw error
        }
        // Network or other errors
        throw new ApiError(0, 'Network error: Unable to connect to backend service. Please ensure the backend server is running.')
    }
}

/**
 * Backend sheet model API
 */
export const sheetModelApi = {
    /**
     * Get the current sheet model from backend
     */
    async get(): Promise<GraphSheetModel> {
        return fetchJson<GraphSheetModel>(`${API_BASE}/config/sheet_model`)
    },

    /**
     * Save sheet model to backend
     */
    async save(model: GraphSheetModel): Promise<void> {
        await fetchJson(`${API_BASE}/config/sheet_model`, {
            method: 'POST',
            body: JSON.stringify(model),
        })
    },

    /**
     * Delete sheet model from backend
     */
    async delete(): Promise<void> {
        await fetchJson(`${API_BASE}/config/sheet_model`, {
            method: 'DELETE',
        })
    },
}

/**
 * Database API
 */
export const databaseApi = {
    /**
     * Get database status
     */
    async getStatus(): Promise<any> {
        return fetchJson(`${API_BASE}/database/status`)
    },

    /**
     * Get database structure
     */
    async getStructure(): Promise<any> {
        return fetchJson(`${API_BASE}/database/db_structure`)
    },

    /**
     * Delete all data
     */
    async deleteAll(): Promise<void> {
        await fetchJson(`${API_BASE}/database/delete_all`, {
            method: 'DELETE',
        })
    },
}

/**
 * Spreadsheet API
 */
export const spreadsheetApi = {
    /**
     * Process spreadsheet
     */
    async process(filePath: string): Promise<any> {
        return fetchJson(`${API_BASE}/spreadsheet/process`, {
            method: 'POST',
            body: JSON.stringify(filePath),
        })
    },

    /**
     * Upload spreadsheet
     */
    async upload(file: File): Promise<string> {
        const formData = new FormData()
        formData.append('file', file)

        const response = await fetch(`${API_BASE}/spreadsheet/upload`, {
            method: 'POST',
            body: formData,
        })

        if (!response.ok) {
            throw new ApiError(response.status, await response.text())
        }

        return response.text()
    },
}
