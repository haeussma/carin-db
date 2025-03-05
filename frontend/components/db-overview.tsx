"use client"

import { useState, useEffect } from "react"
import { Database, FileText, Folder, Users, Package, Server, HardDrive } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, XAxis, YAxis } from "recharts"
import { Button } from "@/components/ui/button"

// Type for our node data
interface NodeData {
    type: string
    count: number
    color: string
}

// Generate an HSL color based on index with good distinction between colors
const generateColor = (index: number, total: number): string => {
    // Use the golden ratio to create well-distributed hues
    const goldenRatioConjugate = 0.618033988749895;

    // Start at a random point and step through hue space
    let hue = (index * goldenRatioConjugate * 360) % 360;

    // Adjust saturation and lightness for better visibility
    const saturation = 70 + (index % 3) * 10; // 70-90%
    const lightness = 55 + (index % 2) * 10;  // 55-65%

    return `hsl(${Math.floor(hue)}, ${saturation}%, ${lightness}%)`;
};

// CSS theme colors (used when available)
const themeColors = [
    "hsl(var(--chart-1))",
    "hsl(var(--chart-2))",
    "hsl(var(--chart-3))",
    "hsl(var(--chart-4))",
    "hsl(var(--chart-5))",
    "hsl(var(--chart-6))",
    "hsl(var(--chart-7, 140, 70%, 50%))",
    "hsl(var(--chart-8, 180, 70%, 50%))",
    "hsl(var(--chart-9, 220, 70%, 50%))",
    "hsl(var(--chart-10, 260, 70%, 50%))",
    "hsl(var(--chart-11, 300, 70%, 50%))",
    "hsl(var(--chart-12, 340, 70%, 50%))",
];

export default function DatabaseNodeVisualization() {
    const [activeTab, setActiveTab] = useState("overview")
    const [nodeData, setNodeData] = useState<NodeData[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Define fetchNodeData outside useEffect so it can be called from JSX
    const fetchNodeData = async () => {
        setIsLoading(true)
        setError(null)

        try {
            const response = await fetch('http://localhost:8000/api/get_node_count')

            // print data
            console.log(response)

            if (!response.ok) {
                throw new Error(`Failed to fetch node data: ${response.statusText}`)
            }

            const data = await response.json()

            // Check if the response contains an error
            if (data.error) {
                throw new Error(data.error)
            }

            // Transform the data into the format we need
            const nodeTypes = Object.keys(data);
            const transformedData: NodeData[] = nodeTypes.map((type, index) => ({
                type,
                count: data[type] as number,
                // Use theme colors when available, fallback to generated colors
                color: index < themeColors.length
                    ? themeColors[index]
                    : generateColor(index, nodeTypes.length)
            }));

            setNodeData(transformedData)
        } catch (err) {
            console.error("Error fetching node data:", err)
            setError(err instanceof Error ? err.message : 'An error occurred while fetching data')

            // If we couldn't fetch data, use empty array
            setNodeData([])
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        fetchNodeData()
    }, [])

    // Calculate total nodes
    const totalNodes = nodeData.reduce((sum, node) => sum + node.count, 0)

    // Format large numbers with commas
    const formatNumber = (num: number) => {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")
    }

    return (
        <div className="container mx-auto p-4 space-y-6">
            <div className="flex flex-col space-y-2">
                <h2 className="text-3xl font-bold tracking-tight">Database Node Visualization</h2>
                <p className="text-muted-foreground">Overview of node distribution in your database</p>
            </div>

            {isLoading ? (
                <Card className="w-full">
                    <CardContent className="pt-6 flex justify-center items-center min-h-[300px]">
                        <div className="flex flex-col items-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
                            <p>Loading node data...</p>
                        </div>
                    </CardContent>
                </Card>
            ) : error ? (
                <Card className="w-full">
                    <CardContent className="pt-6 flex justify-center items-center min-h-[300px]">
                        <div className="flex flex-col items-center text-center max-w-xl">
                            <div className="text-red-500 text-4xl mb-4">⚠️</div>
                            <h3 className="text-xl font-semibold mb-2">Database Connection Error</h3>

                            {/* Format the error message with line breaks */}
                            <div className="text-muted-foreground text-left">
                                {error.split('\n').map((line, i) => (
                                    <p key={i} className={i > 0 ? "mt-2" : ""}>
                                        {line}
                                    </p>
                                ))}
                            </div>

                            {/* Different actions based on error type */}
                            {error.includes("Database connection settings") && (
                                <div className="mt-4">
                                    <p className="text-sm mb-2">
                                        Configure your database connection in settings to continue.
                                    </p>
                                    <Button
                                        variant="outline"
                                        onClick={() => {
                                            // Open settings dialog by simulating a click on the settings button
                                            const settingsButton = document.querySelector('[data-settings-button]');
                                            if (settingsButton instanceof HTMLElement) {
                                                settingsButton.click();
                                            }
                                        }}
                                    >
                                        Open Settings
                                    </Button>
                                </div>
                            )}
                            {error.includes("Cannot connect to Neo4j database") && (
                                <div className="mt-4">
                                    <p className="text-sm mb-2">
                                        Check your Neo4j server status and network settings.
                                    </p>
                                    <div className="flex gap-2">
                                        <Button
                                            variant="outline"
                                            onClick={() => {
                                                // Open settings dialog
                                                const settingsButton = document.querySelector('[data-settings-button]');
                                                if (settingsButton instanceof HTMLElement) {
                                                    settingsButton.click();
                                                }
                                            }}
                                        >
                                            Open Settings
                                        </Button>
                                        <Button
                                            variant="default"
                                            onClick={() => {
                                                // Retry the data fetch
                                                fetchNodeData();
                                            }}
                                        >
                                            Retry Connection
                                        </Button>
                                    </div>
                                </div>
                            )}
                            {error.includes("Authentication failed") && (
                                <div className="mt-4">
                                    <p className="text-sm mb-2">
                                        Update your Neo4j username and password to continue.
                                    </p>
                                    <Button
                                        variant="outline"
                                        onClick={() => {
                                            // Open settings dialog
                                            const settingsButton = document.querySelector('[data-settings-button]');
                                            if (settingsButton instanceof HTMLElement) {
                                                settingsButton.click();
                                            }
                                        }}
                                    >
                                        Open Settings
                                    </Button>
                                </div>
                            )}
                            {!error.includes("Database connection settings") &&
                                !error.includes("Cannot connect to Neo4j database") &&
                                !error.includes("Authentication failed") && (
                                    <div className="mt-4">
                                        <p className="text-sm mb-2">
                                            Please check your database connection and try again.
                                        </p>
                                        <Button
                                            variant="default"
                                            onClick={() => fetchNodeData()}
                                        >
                                            Retry
                                        </Button>
                                    </div>
                                )}
                        </div>
                    </CardContent>
                </Card>
            ) : nodeData.length === 0 ? (
                <Card className="w-full">
                    <CardContent className="pt-6 flex justify-center items-center min-h-[300px]">
                        <div className="flex flex-col items-center text-center">
                            <Database className="text-muted-foreground h-12 w-12 mb-4" />
                            <h3 className="text-xl font-semibold mb-2">No Data Available</h3>
                            <p className="text-muted-foreground">
                                There are no nodes in your database yet.
                            </p>
                            <p className="mt-4 text-sm">
                                Start by importing data or creating nodes.
                            </p>
                        </div>
                    </CardContent>
                </Card>
            ) : (
                <div className="flex items-center justify-between">
                    <Card className="w-full">
                        <CardHeader>
                            <CardTitle>Node Distribution</CardTitle>
                            <CardDescription>
                                Total of {formatNumber(totalNodes)} nodes in the database
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Tabs value={activeTab} onValueChange={setActiveTab}>
                                <TabsList className="mb-4">
                                    <TabsTrigger value="overview">Overview</TabsTrigger>
                                    <TabsTrigger value="pie">Pie Chart</TabsTrigger>
                                    <TabsTrigger value="bar">Bar Chart</TabsTrigger>
                                </TabsList>
                                <TabsContent value="overview" className="space-y-4">
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                        {nodeData.map((nodeType) => (
                                            <Card key={nodeType.type}>
                                                <CardContent className="p-4 flex items-center justify-between">
                                                    <div className="flex items-center">
                                                        {getIconForNodeType(nodeType.type)}
                                                        <div className="ml-4">
                                                            <p className="text-sm font-medium">{nodeType.type}</p>
                                                            <p className="text-2xl font-bold">{formatNumber(nodeType.count)}</p>
                                                        </div>
                                                    </div>
                                                    <div
                                                        className="h-12 w-12 rounded-full opacity-20"
                                                        style={{ backgroundColor: nodeType.color }}
                                                    />
                                                </CardContent>
                                            </Card>
                                        ))}
                                    </div>
                                </TabsContent>
                                <TabsContent value="pie">
                                    <div className="h-[300px]">
                                        <ChartContainer
                                            config={nodeData.reduce(
                                                (acc, node) => {
                                                    acc[node.type] = {
                                                        label: node.type,
                                                        color: node.color,
                                                    }
                                                    return acc
                                                },
                                                {} as Record<string, { label: string; color: string }>
                                            )}
                                        >
                                            <PieChart>
                                                <Pie
                                                    data={nodeData}
                                                    cx="50%"
                                                    cy="50%"
                                                    outerRadius={100}
                                                    dataKey="count"
                                                    nameKey="type"
                                                    label={({ type, count }) => `${type}: ${formatNumber(count)}`}
                                                >
                                                    {nodeData.map((entry, index) => (
                                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                                    ))}
                                                </Pie>
                                                <ChartTooltip content={<ChartTooltipContent />} />
                                            </PieChart>
                                        </ChartContainer>
                                    </div>
                                </TabsContent>
                                <TabsContent value="bar">
                                    <div className="h-[300px]">
                                        <ChartContainer
                                            config={nodeData.reduce(
                                                (acc, node) => {
                                                    acc[node.type] = {
                                                        label: node.type,
                                                        color: node.color,
                                                    }
                                                    return acc
                                                },
                                                {} as Record<string, { label: string; color: string }>
                                            )}
                                        >
                                            <BarChart data={nodeData}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="type" />
                                                <YAxis />
                                                <Bar dataKey="count">
                                                    {nodeData.map((entry, index) => (
                                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                                    ))}
                                                </Bar>
                                                <ChartTooltip content={<ChartTooltipContent />} />
                                            </BarChart>
                                        </ChartContainer>
                                    </div>
                                </TabsContent>
                            </Tabs>
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    )
}

// Helper function to get an icon based on node type
function getIconForNodeType(type: string) {
    const iconProps = { className: "h-6 w-6" }

    // Map common biological/chemical entity names to appropriate icons
    switch (type.toLowerCase()) {
        // Original mappings
        case 'user':
            return <Users {...iconProps} />
        case 'document':
            return <FileText {...iconProps} />
        case 'collection':
            return <Folder {...iconProps} />
        case 'product':
            return <Package {...iconProps} />
        case 'server':
            return <Server {...iconProps} />
        case 'storage':
            return <HardDrive {...iconProps} />

        // New mappings for biological/chemical entities
        case 'molecule':
        case 'compound':
            return <Database {...iconProps} />
        case 'enzyme':
        case 'biocatalyst':
            return <Package {...iconProps} />
        case 'peak':
        case 'signal':
            return <HardDrive {...iconProps} />
        case 'reaction':
        case 'process':
            return <Server {...iconProps} />
        case 'sampling':
        case 'sample':
            return <FileText {...iconProps} />

        // Default icon for any other type
        default:
            // If we can't find a specific icon, use the first letter of the type as an icon
            return (
                <div
                    className="flex items-center justify-center h-6 w-6 rounded-full bg-primary/10 text-primary font-semibold text-xs"
                >
                    {type.charAt(0).toUpperCase()}
                </div>
            )
    }
}

