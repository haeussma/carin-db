import type { GraphSheetModel } from "./types"

export interface ValidationIssue {
  kind: string
  message: string
  node?: string
  prop?: string
  edgeId?: string
}

export function validateModel(model: GraphSheetModel): ValidationIssue[] {
  const issues: ValidationIssue[] = []

  model.sheets.forEach((node) => {
    const nodeName = node.name

    // Check unique property exists
    if (node.unique_property && !(node.properties || []).find((p) => p.name === node.unique_property)) {
      issues.push({
        kind: "missing_unique_property",
        message: `Unique property "${node.unique_property}" not found in properties`,
        node: nodeName,
      })
    }

    // Check property names and references
    (node.properties || []).forEach((prop) => {
      if (!prop.name || !prop.name.trim()) {
        issues.push({
          kind: "empty_property_name",
          message: "Property name cannot be empty",
          node: nodeName,
          prop: prop.name || "",
        })
      }

      // Check ref properties
      if (prop.config && prop.config.kind === "ref") {
        const targetNode = model.sheets.find((n) => n.name === prop.config.to)
        if (!targetNode) {
          issues.push({
            kind: "invalid_ref_target",
            message: `Reference target "${prop.config.to}" does not exist`,
            node: nodeName,
            prop: prop.name,
            edgeId: `${nodeName}.${prop.name}`,
          })
        } else {
          if (model.enforce_ref_on_unique && prop.config.on !== targetNode.unique_property) {
            issues.push({
              kind: "ref_not_on_unique",
              message: `Reference must point to unique property "${targetNode.unique_property}"`,
              node: nodeName,
              prop: prop.name,
              edgeId: `${nodeName}.${prop.name}`,
            })
          }
        }
      }
    })
  })

  return issues
}

export function computeProgress(model: GraphSheetModel, issues: ValidationIssue[]): number {
  const totalNodes = model.sheets.length
  if (totalNodes === 0) return 0

  const totalProperties = model.sheets.reduce((sum, node) => sum + (node.properties || []).length, 0)

  const totalItems = totalNodes + totalProperties
  const issueCount = issues.length

  return Math.max(0, Math.round(((totalItems - issueCount) / totalItems) * 100))
}
