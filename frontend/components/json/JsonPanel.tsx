"use client"

import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { useSchemaStore } from "@/store/useSchemaStore"
import { Copy, Download, AlertCircle, CheckCircle } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

export function JsonPanel() {
  const { model, issues, progress, exportJson } = useSchemaStore()
  const { toast } = useToast()

  const handleCopy = () => {
    navigator.clipboard.writeText(exportJson())
    toast({ title: "Copied", description: "JSON copied to clipboard" })
  }

  const handleDownload = () => {
    const json = exportJson()
    const blob = new Blob([json], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "graph_sheet_model.json"
    a.click()
    URL.revokeObjectURL(url)
  }

  const groupedIssues = issues.reduce(
    (acc, issue) => {
      const key = issue.node || "Global"
      if (!acc[key]) acc[key] = []
      acc[key].push(issue)
      return acc
    },
    {} as Record<string, typeof issues>,
  )

  return (
    <div className="h-full flex flex-col border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium">Configuration</h3>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleCopy}>
              <Copy className="h-4 w-4 mr-2" />
              Copy
            </Button>
            <Button variant="outline" size="sm" onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span>Validation Progress</span>
            <span>{progress}%</span>
          </div>
          <Progress value={progress} className="h-2" />

          {issues.length > 0 && (
            <div className="flex items-center gap-1 text-xs text-destructive">
              <AlertCircle className="h-3 w-3" />
              {issues.length} issue{issues.length !== 1 ? "s" : ""} found
            </div>
          )}

          {issues.length === 0 && progress === 100 && (
            <div className="flex items-center gap-1 text-xs text-green-600">
              <CheckCircle className="h-3 w-3" />
              Configuration is valid
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        {issues.length > 0 && (
          <div className="p-4 border-b">
            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="issues">
                <AccordionTrigger className="text-sm">Validation Issues ({issues.length})</AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-2">
                    {Object.entries(groupedIssues).map(([nodeOrGlobal, nodeIssues]) => (
                      <div key={nodeOrGlobal}>
                        <h4 className="text-xs font-medium text-muted-foreground mb-1">{nodeOrGlobal}</h4>
                        {nodeIssues.map((issue, index) => (
                          <Alert key={index} className="py-2">
                            <AlertCircle className="h-3 w-3" />
                            <AlertDescription className="text-xs">{issue.message}</AlertDescription>
                          </Alert>
                        ))}
                      </div>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </div>
        )}

        <ScrollArea className="flex-1 p-4">
          <pre className="text-xs font-mono whitespace-pre-wrap break-words">{JSON.stringify(model, null, 2)}</pre>
        </ScrollArea>
      </div>
    </div>
  )
}
