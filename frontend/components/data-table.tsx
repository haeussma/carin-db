'use client'

import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

// This type is a placeholder. Adjust it based on your actual data structure.
type DataItem = Record<string, any>  // Use 'any' to accommodate nested objects

function renderCellValue(value: any) {
    if (value === null || value === undefined) {
        return ''
    } else if (typeof value === 'object') {
        // Format the object as needed. Here, we'll stringify it.
        return JSON.stringify(value)
    } else {
        return value.toString()
    }
}

export default function DataTableCard() {
    const [question, setQuery] = useState('')
    const [data, setData] = useState<DataItem[]>([])
    const [isLoading, setIsLoading] = useState(false)

    const handleSend = async () => {
        setIsLoading(true);
        try {
            const response = await fetch('http://localhost:8000/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question })
            });
            const result = await response.json();
            console.log('Data received:', result.result); // Should be an array of objects
            setData(result.result || []);
        } catch (error) {
            console.error('Error fetching data:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSaveToFile = async () => {
        try {
            // Replace with your actual API endpoint
            const response = await fetch('http://localhost:8000/api/generateSpreadsheet', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data })
            })
            const blob = await response.blob()
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.style.display = 'none'
            a.href = url
            a.download = 'data.xlsx'
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
        } catch (error) {
            console.error('Error generating spreadsheet:', error)
        }
    }

    return (
        <Card className="w-full max-w-4xl mx-auto">
            <CardHeader>
                <CardTitle className="text-2xl font-bold text-center">Search</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <Textarea
                        placeholder="What data are you looking for?"
                        value={question}
                        onChange={(e) => setQuery(e.target.value)}
                        className="min-h-[100px]"
                    />
                    <Button onClick={handleSend} disabled={isLoading} className="w-full">
                        {isLoading ? 'searching...' : 'Search'}
                    </Button>
                </div>
                {data.length > 0 && (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                {Object.keys(data[0]).map((key) => (
                                    <TableHead key={key}>{key}</TableHead>
                                ))}
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {data.map((item, index) => (
                                <TableRow key={index}>
                                    {Object.values(item).map((value, valueIndex) => (
                                        <TableCell key={valueIndex}>
                                            {renderCellValue(value)}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}
            </CardContent>
            <CardFooter>
                <Button onClick={handleSaveToFile} disabled={data.length === 0} className="w-full">
                    Save to file
                </Button>
            </CardFooter>
        </Card>
    )
}
