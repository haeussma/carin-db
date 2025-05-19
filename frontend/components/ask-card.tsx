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
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!question) return;

        const apiKey = localStorage.getItem('openai_api_key');
        if (!apiKey) {
            setError('Please set your OpenAI API key in settings first');
            return;
        }

        setIsSubmitting(true);

        try {
            const response = await fetch('/api/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-OpenAI-Key': apiKey
                },
                body: JSON.stringify({
                    question,
                    export: exportAsSpreadsheet,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || errorData.detail || 'Request failed');
            }

            if (exportAsSpreadsheet) {
                // Handle file download
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', 'data.xlsx');
                document.body.appendChild(link);
                link.click();
                link.parentNode?.removeChild(link);
            } else {
                // Handle text response
                const data = await response.json();
                setAnswer(data.result ? JSON.stringify(data.result, null, 2) : data.answer);
            }
        } catch (error: any) {
            console.error('Error:', error);
            setError(error.message || 'Failed to get response');
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
                    {error && (
                        <div className="text-red-500 text-sm">{error}</div>
                    )}
                </CardContent>
                <CardFooter>
                    <Button type="submit" className="w-full" disabled={isSubmitting || !question}>
                        {isSubmitting ? 'Submitting...' : 'Ask'}
                    </Button>
                </CardFooter>
            </form>
            {answer && (
                <div className="p-4 mt-4 bg-muted rounded-lg">
                    <h4 className="text-lg font-semibold mb-2">Answer:</h4>
                    <pre className="whitespace-pre-wrap">{answer}</pre>
                </div>
            )}
        </Card>
    );
}
