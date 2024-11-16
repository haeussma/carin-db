'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, ArrowRight, X } from 'lucide-react'

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface Relationship {
  source: string
  name: string
  target: string
}

export default function SpreadsheetUploader() {
  const [file, setFile] = useState<File | null>(null)
  const [primaryKey, setPrimaryKey] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [relationships, setRelationships] = useState<Relationship[]>([])

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFile(acceptedFiles[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv']
    },
    multiple: false
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !primaryKey) return

    setIsUploading(true)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('primary_key', primaryKey) // Use 'primary_key' to match backend
    formData.append('relationships', JSON.stringify(relationships))

    try {
      const response = await fetch('http://localhost:8000/api/process_file', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      alert('Spreadsheet and relationships uploaded successfully!')
      setFile(null)
      setPrimaryKey('')
      setRelationships([])
    } catch (error: any) {
      console.error('Error uploading spreadsheet:', error)
      alert(`Failed to upload spreadsheet: ${error.message}`)
    } finally {
      setIsUploading(false)
    }
  }

  const addRelationship = () => {
    setRelationships([...relationships, { source: '', name: '', target: '' }])
  }

  const updateRelationship = (index: number, field: keyof Relationship, value: string) => {
    const updatedRelationships = relationships.map((rel, i) =>
      i === index ? { ...rel, [field]: value } : rel
    )
    setRelationships(updatedRelationships)
  }

  const deleteRelationship = (index: number) => {
    setRelationships(relationships.filter((_, i) => i !== index))
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="text-2xl font-bold text-center">Upload Spreadsheet</CardTitle>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-6">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-md p-4 text-center cursor-pointer transition-colors ${isDragActive ? 'border-primary bg-primary/10' : 'border-gray-300 hover:border-primary'
              }`}
          >
            <input {...getInputProps()} />
            {file ? (
              <div className="flex items-center justify-center space-x-2">
                <File className="w-6 h-6 text-primary" />
                <span className="font-medium">{file.name}</span>
              </div>
            ) : (
              <div>
                <Upload className="w-8 h-8 mx-auto text-gray-400" />
                <p className="mt-2">Drag &amp; drop a spreadsheet here, or click to select one</p>
                <p className="text-sm text-gray-500">(Supports .xlsx, .xls, and .csv files)</p>
              </div>
            )}
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold">Primary Key</h3>
            </div>
            <Input
              id="primaryKey"
              value={primaryKey}
              onChange={(e) => setPrimaryKey(e.target.value)}
              placeholder="Enter the primary key"
            />
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold">Relationships</h3>
              <Button type="button" onClick={addRelationship} variant="outline">
                Add new Relation
              </Button>
            </div>
            {relationships.map((rel, index) => (
              <div key={index} className="flex items-center space-x-2 bg-muted p-4 rounded-md">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Input
                        value={rel.source}
                        onChange={(e) => updateRelationship(index, 'source', e.target.value)}
                        placeholder="Source"
                        className="w-1/3"
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Must match a sheet name in the Excel file</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <ArrowRight className="w-6 h-6 text-muted-foreground flex-shrink-0" />
                <Input
                  value={rel.name}
                  onChange={(e) => updateRelationship(index, 'name', e.target.value)}
                  placeholder="Relation Name"
                  className="w-1/3"
                />
                <ArrowRight className="w-6 h-6 text-muted-foreground flex-shrink-0" />
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Input
                        value={rel.target}
                        onChange={(e) => updateRelationship(index, 'target', e.target.value)}
                        placeholder="Target"
                        className="w-1/3"
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Must match a sheet name in the Excel file</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => deleteRelationship(index)}
                  className="flex-shrink-0"
                >
                  <X className="h-4 w-4" />
                  <span className="sr-only">Delete relationship</span>
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
        <CardFooter>
          <Button
            type="submit"
            className="w-full"
            disabled={!file || !primaryKey || isUploading}
          >
            {isUploading ? 'Uploading...' : 'Add to Graph'}
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}
