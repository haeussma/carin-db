'use client'

import { useState, useMemo } from 'react'
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

// This type is a placeholder. Adjust it based on your actual data structure.
type DataItem = Record<string, any>  // Use 'any' to accommodate nested objects

function renderCellValue(value: any) {
    if (value === null || value === undefined) {
        return '-'
    } else if (Array.isArray(value)) {
        return (
            <div className="max-h-40 overflow-y-auto">
                {value.map((item, i) => (
                    <div key={i} className="mb-1 pb-1 border-b border-gray-100">
                        {renderCellValue(item)}
                    </div>
                ))}
            </div>
        )
    } else if (typeof value === 'object') {
        // Format the object for better readability
        return (
            <div className="max-h-40 overflow-y-auto text-xs">
                {Object.entries(value).map(([k, v]) => (
                    <div key={k} className="mb-1">
                        <span className="font-semibold">{k}: </span>
                        <span>{typeof v === 'object' ? JSON.stringify(v) : String(v || '-')}</span>
                    </div>
                ))}
            </div>
        )
    } else {
        return String(value)
    }
}

// Function to flatten nested objects for table display
function flattenNestedData(data: DataItem[]): {
    flattenedData: DataItem[],
    headers: { key: string, label: string }[]
} {
    if (!data || data.length === 0) return { flattenedData: [], headers: [] };

    // Check if we have a nested structure with 'm' and other keys
    const hasNestedStructure = data.some(item =>
        item.m && typeof item.m === 'object' && Object.keys(item).length <= 3);

    if (!hasNestedStructure) {
        // For regular data, just return as is with simple headers
        const headers = Object.keys(data[0]).map(key => ({ key, label: key }));
        return { flattenedData: data, headers };
    }

    // For nested data, flatten it
    const flattenedData: DataItem[] = [];
    const allProperties = new Set<string>();

    // First pass: collect all possible properties
    data.forEach(item => {
        if (item.m && typeof item.m === 'object') {
            Object.keys(item.m).forEach(key => allProperties.add(key));
        }
    });

    // Second pass: create flattened rows
    data.forEach((item, index) => {
        const flatItem: DataItem = { index: index + 1 };

        if (item.m && typeof item.m === 'object') {
            Object.entries(item.m).forEach(([key, value]) => {
                flatItem[key] = value;
            });
        }

        flattenedData.push(flatItem);
    });

    // Create headers
    const headers = [
        { key: 'index', label: '#' },
        ...Array.from(allProperties).map(prop => ({ key: prop, label: prop }))
    ];

    return { flattenedData, headers };
}

export default function DataTableCard() {
    const [question, setQuery] = useState('')
    const [data, setData] = useState<DataItem[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [errorMessage, setErrorMessage] = useState<string>('')
    const [viewMode, setViewMode] = useState<'flat' | 'raw'>('flat')

    // Process the data for display
    const { flattenedData, headers } = useMemo(() =>
        flattenNestedData(data), [data]);

    const handleSend = async () => {
        setIsLoading(true);
        setErrorMessage(''); // Clear any previous error messages
        setData([]);

        try {
            const response = await fetch('http://localhost:8000/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question })
            });

            const result = await response.json();
            console.log('Result:', result);

            if (!response.ok) {
                // Handle error response from the API
                let errorMsg = 'An error occurred';

                // Extract error message from the response
                if (result.detail && result.detail.error && result.detail.error.message) {
                    errorMsg = result.detail.error.message;
                } else if (result.detail) {
                    errorMsg = typeof result.detail === 'string' ? result.detail : JSON.stringify(result.detail);
                }

                console.error('API error:', errorMsg);
                setErrorMessage(errorMsg);
                return;
            }

            // Process the response data
            if (result.response) {
                // Check if response is an array
                if (Array.isArray(result.response)) {
                    console.log('Data received (array):', result.response);

                    // Handle empty array
                    if (result.response.length === 0) {
                        setErrorMessage('No data found for your query');
                        return;
                    }

                    // Process the array data
                    setData(result.response);
                } else if (typeof result.response === 'object') {
                    // Handle single object response
                    console.log('Data received (object):', result.response);
                    setData([result.response]);
                } else {
                    // Handle string or other primitive response
                    console.log('Data received (primitive):', result.response);
                    setData([{ response: result.response }]);
                }
            } else if (result.result && Array.isArray(result.result)) {
                // For backward compatibility, if result field exists and is an array
                console.log('Data received (result field):', result.result);
                setData(result.result);
            } else {
                // If neither expected format is found
                console.warn('Unexpected response format:', result);
                setErrorMessage('Received an unexpected response format from the server');
            }
        } catch (error) {
            console.error('Error fetching data:', error);
            setErrorMessage('Failed to connect to the server. Please check if the backend is running.');
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

                {/* Display error message if there is one */}
                {errorMessage && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative" role="alert">
                        <strong className="font-bold">Error: </strong>
                        <span className="block sm:inline">{errorMessage}</span>
                    </div>
                )}

                {data.length > 0 && (
                    <div className="space-y-2">
                        <div className="flex justify-end space-x-2">
                            <Button
                                variant={viewMode === 'flat' ? "default" : "outline"}
                                size="sm"
                                onClick={() => setViewMode('flat')}
                            >
                                Flattened View
                            </Button>
                            <Button
                                variant={viewMode === 'raw' ? "default" : "outline"}
                                size="sm"
                                onClick={() => setViewMode('raw')}
                            >
                                Raw View
                            </Button>
                        </div>

                        {viewMode === 'flat' ? (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        {headers.map((header) => (
                                            <TableHead key={header.key}>{header.label}</TableHead>
                                        ))}
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {flattenedData.map((item, rowIndex) => (
                                        <TableRow key={rowIndex}>
                                            {headers.map((header) => (
                                                <TableCell key={`${rowIndex}-${header.key}`}>
                                                    {item[header.key] !== undefined ?
                                                        (typeof item[header.key] === 'object' ?
                                                            JSON.stringify(item[header.key]) :
                                                            String(item[header.key])) :
                                                        '-'}
                                                </TableCell>
                                            ))}
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ) : (
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
                    </div>
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
