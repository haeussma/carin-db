'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File } from 'lucide-react'

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

export function SpreadsheetUploaderComponent() {
  const [file, setFile] = useState<File | null>(null)
  const [primaryKey, setPrimaryKey] = useState('')
  const [isUploading, setIsUploading] = useState(false)

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
    formData.append('primary_key', primaryKey)

    try {
      // Replace with your actual API endpoint
      const response = await fetch('http://localhost:8000/api/process_file', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        alert('Spreadsheet uploaded successfully!')
        setFile(null)
        setPrimaryKey('')
      } else {
        throw new Error('Upload failed')
      }
    } catch (error) {
      console.error('Error uploading spreadsheet:', error)
      alert('Failed to upload spreadsheet. Please try again.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="text-2xl font-bold text-center">Upload Spreadsheet</CardTitle>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-md p-2 text-center cursor-pointer transition-colors ${isDragActive ? 'border-primary bg-primary/10' : 'border-gray-300 hover:border-primary'
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
          <div className="space-y-2">
            <Label htmlFor="primaryKey">Primary Key</Label>
            <Input
              id="primaryKey"
              value={primaryKey}
              onChange={(e) => setPrimaryKey(e.target.value)}
              placeholder="Enter the primary key"
            />
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