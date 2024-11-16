'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from './ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

export default function AskCard() {
    const [question, setQuestion] = useState('');
    const [exportAsSpreadsheet, setExportAsSpreadsheet] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [answer, setAnswer] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!question) return;

        setIsSubmitting(true);

        try {
            const response = await fetch('http://localhost:8000/api/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question,
                    export: exportAsSpreadsheet,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Request failed');
            }

            if (exportAsSpreadsheet) {
                // Handle file download
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', 'data.xlsx'); // You can change the filename as needed
                document.body.appendChild(link);
                link.click();
                link.parentNode?.removeChild(link);
            } else {
                // Handle text response
                const data = await response.json();
                setAnswer(data.answer);
            }
        } catch (error: any) {
            console.error('Error:', error);
            alert(`Failed to get response: ${error.message}`);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Card className="w-full max-w-4xl mx-auto p-8">
            <CardHeader>
                <CardTitle className="text-2xl font-bold text-center">Ask</CardTitle>
            </CardHeader>
            <form onSubmit={handleSubmit}>
                <CardContent className="space-y-4">
                    <Textarea
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder="Enter your question here"
                        className="w-full"
                    />
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="exportAsSpreadsheet"
                            checked={exportAsSpreadsheet}
                            onCheckedChange={(checked) => setExportAsSpreadsheet(!!checked)}
                        />
                        <label htmlFor="exportAsSpreadsheet" className="text-sm">
                            Export data as spreadsheet
                        </label>
                    </div>
                </CardContent>
                <CardFooter>
                    <Button type="submit" className="w-full" disabled={isSubmitting || !question}>
                        {isSubmitting ? 'Submitting...' : 'Send'}
                    </Button>
                </CardFooter>
            </form>
            {answer && (
                <div className="p-4">
                    <h4 className="text-lg font-semibold">Answer:</h4>
                    <p>{answer}</p>
                </div>
            )}
        </Card>
    );
}
