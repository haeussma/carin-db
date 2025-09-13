import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, FileX, Type, Hash } from "lucide-react";

interface SpreadsheetValidationError {
    error: string;
    message: string;
    sheet_name_errors: Array<{
        sheet_name: string;
        path: string;
    }>;
    column_name_errors: Array<{
        sheet_name: string;
        column: string;
        path: string;
    }>;
    column_type_inconsistencies: Array<{
        sheet_name: string;
        column: string;
        first_inconsistency: number;
        path: string;
    }>;
}

interface SpreadsheetErrorDialogProps {
    error: SpreadsheetValidationError | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

function groupColumnNameErrorsBySheet(
    columnNameErrors: SpreadsheetValidationError["column_name_errors"]
): Record<string, Set<string>> {
    // Returns: { [sheetName]: Set of column names with errors }
    const grouped: Record<string, Set<string>> = {};
    for (const err of columnNameErrors) {
        if (!grouped[err.sheet_name]) {
            grouped[err.sheet_name] = new Set();
        }
        grouped[err.sheet_name].add(err.column);
    }
    return grouped;
}

export function SpreadsheetErrorDialog({
    error,
    open,
    onOpenChange,
}: SpreadsheetErrorDialogProps) {
    if (!error) return null;

    // Be defensive about missing fields
    const sheetNameErrors = error.sheet_name_errors || [];
    const columnNameErrors = error.column_name_errors || [];
    const columnTypeInconsistencies = error.column_type_inconsistencies || [];

    const totalErrors =
        sheetNameErrors.length +
        Object.keys(groupColumnNameErrorsBySheet(columnNameErrors)).length +
        columnTypeInconsistencies.length;

    // Group column name errors by sheet for high-level summary
    const columnNameErrorsBySheet = groupColumnNameErrorsBySheet(columnNameErrors);

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-destructive">
                        <AlertTriangle className="h-5 w-5" />
                        Spreadsheet Validation Failed
                    </DialogTitle>
                    <DialogDescription>
                        Found {totalErrors} validation error
                        {totalErrors !== 1 ? "s" : ""} in your spreadsheet. Please fix these
                        issues and try uploading again.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    {/* Sheet Name Errors */}
                    {sheetNameErrors.length > 0 && (
                        <Card className="border-destructive/20">
                            <CardHeader className="pb-3">
                                <CardTitle className="flex items-center gap-2 text-sm font-medium text-destructive">
                                    <FileX className="h-4 w-4" />
                                    Sheet Name Errors
                                    <Badge variant="destructive" className="ml-auto">
                                        {sheetNameErrors.length}
                                    </Badge>
                                </CardTitle>
                                <CardDescription className="text-xs">
                                    Issues with sheet names in your spreadsheet
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-2">
                                {sheetNameErrors.map((sheetError, index) => (
                                    <Card key={index} className="bg-muted/50">
                                        <CardContent className="p-3">
                                            <div className="space-y-1">
                                                <div className="flex items-center justify-between">
                                                    <span className="font-medium text-sm">
                                                        Sheet: {sheetError.sheet_name}
                                                    </span>
                                                    <Badge variant="outline" className="text-xs">
                                                        Error #{index + 1}
                                                    </Badge>
                                                </div>
                                                <p className="text-xs text-muted-foreground">
                                                    Path: {sheetError.path}
                                                </p>
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))}
                            </CardContent>
                        </Card>
                    )}

                    {/* Column Name Errors (Grouped by Sheet, high-level) */}
                    {Object.keys(columnNameErrorsBySheet).length > 0 && (
                        <Card className="border-destructive/20">
                            <CardHeader className="pb-3">
                                <CardTitle className="flex items-center gap-2 text-sm font-medium text-destructive">
                                    <Type className="h-4 w-4" />
                                    Column Name Errors
                                    <Badge variant="destructive" className="ml-auto">
                                        {Object.values(columnNameErrorsBySheet).reduce(
                                            (acc, cols) => acc + cols.size,
                                            0
                                        )}
                                    </Badge>
                                </CardTitle>
                                <CardDescription className="text-xs">
                                    Issues with column names in your spreadsheet.
                                    <br />
                                    Potential issues: extra spaces or illegal characters (e.g., /, \, ?, *, [, ], etc.).
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-2">
                                {Object.entries(columnNameErrorsBySheet).map(
                                    ([sheetName, columns], idx) => (
                                        <Card key={sheetName} className="bg-muted/50">
                                            <CardContent className="p-3">
                                                <div className="space-y-1">
                                                    <div className="flex items-center justify-between">
                                                        <span className="font-medium text-sm">
                                                            Sheet: {sheetName}
                                                        </span>
                                                        <Badge variant="outline" className="text-xs">
                                                            {columns.size} column
                                                            {columns.size !== 1 ? "s" : ""} with issues
                                                        </Badge>
                                                    </div>
                                                    <div className="flex flex-wrap gap-2 mt-1">
                                                        {[...columns].map((col) => (
                                                            <Badge
                                                                key={col}
                                                                variant="secondary"
                                                                className="text-xs"
                                                            >
                                                                {col}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    )
                                )}
                            </CardContent>
                        </Card>
                    )}

                    {/* Column Type Inconsistencies */}
                    {columnTypeInconsistencies.length > 0 && (
                        <Card className="border-destructive/20">
                            <CardHeader className="pb-3">
                                <CardTitle className="flex items-center gap-2 text-sm font-medium text-destructive">
                                    <Hash className="h-4 w-4" />
                                    Column Type Inconsistencies
                                    <Badge variant="destructive" className="ml-auto">
                                        {columnTypeInconsistencies.length}
                                    </Badge>
                                </CardTitle>
                                <CardDescription className="text-xs">
                                    Data type inconsistencies found in columns
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-2">
                                {columnTypeInconsistencies.map((typeError, index) => (
                                    <Card key={index} className="bg-muted/50">
                                        <CardContent className="p-3">
                                            <div className="space-y-1">
                                                <div className="flex items-center justify-between">
                                                    <span className="font-medium text-sm">
                                                        Column: {typeError.column}
                                                    </span>
                                                    <Badge variant="outline" className="text-xs">
                                                        Error #{index + 1}
                                                    </Badge>
                                                </div>
                                                <p className="text-xs text-muted-foreground">
                                                    Sheet: {typeError.sheet_name}
                                                </p>
                                                <p className="text-xs text-muted-foreground">
                                                    First inconsistency at row:{" "}
                                                    {typeError.first_inconsistency + 1}
                                                </p>
                                                <p className="text-xs text-muted-foreground">
                                                    Path: {typeError.path}
                                                </p>
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))}
                            </CardContent>
                        </Card>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
