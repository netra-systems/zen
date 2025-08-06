
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Check, Clipboard, Filter, ChevronDown, ChevronUp } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuCheckboxItem, DropdownMenuTrigger } from '@/app/components/ui/dropdown-menu.tsx';

interface ArtifactData {
    [key: string]: any;
}

interface MessageArtifactProps {
    data: ArtifactData;
}

const JsonTreeView = ({ data, level = 0 }: { data: any, level?: number }) => {
    if (typeof data !== 'object' || data === null) {
        return <span className="text-sm text-muted-foreground">{String(data)}</span>;
    }

    const entries = Object.entries(data);

    return (
        <div className={`pl-${level * 4}`}>
            {entries.map(([key, value]) => (
                <div key={key} className="flex flex-col">
                    <span className="text-sm font-semibold text-primary">{key}:</span>
                    <JsonTreeView data={value} level={level + 1} />
                </div>
            ))}
        </div>
    );
};

export const MessageArtifact = ({ data }: MessageArtifactProps) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [isCopied, setIsCopied] = useState(false);
    const [filters, setFilters] = useState<Record<string, boolean>>({
        on_chain_start: true,
        on_chain_end: true,
        on_chain_stream: true,
        on_prompt_start: true,
        on_prompt_end: true,

    });

    const toggleExpand = () => setIsExpanded(!isExpanded);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(JSON.stringify(data, null, 2));
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
    };

    const handleFilterChange = (filter: string) => {
        setFilters(prev => ({ ...prev, [filter]: !prev[filter] }));
    };

    const filteredData = Object.entries(data)
        .filter(([key]) => filters[key] !== false)
        .reduce((obj, [key, value]) => ({ ...obj, [key]: value }), {});

    return (
        <Card className="w-full max-w-2xl mx-auto my-4 shadow-lg rounded-lg border">
            <CardHeader className="flex flex-row items-center justify-between p-4 bg-muted/50">
                <CardTitle className="text-lg font-semibold">Agent Thinking Process</CardTitle>
                <div className="flex items-center gap-2">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" size="sm">
                                <Filter className="h-4 w-4 mr-2" />
                                Filter
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                            {Object.keys(filters).map(filter => (
                                <DropdownMenuCheckboxItem
                                    key={filter}
                                    checked={filters[filter]}
                                    onCheckedChange={() => handleFilterChange(filter)}
                                >
                                    {filter}
                                </DropdownMenuCheckboxItem>
                            ))}
                        </DropdownMenuContent>
                    </DropdownMenu>
                    <Button variant="outline" size="sm" onClick={copyToClipboard}>
                        {isCopied ? <Check className="h-4 w-4 text-green-500" /> : <Clipboard className="h-4 w-4" />}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={toggleExpand}>
                        {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                    </Button>
                </div>
            </CardHeader>
            {isExpanded && (
                <CardContent className="p-4 bg-background overflow-x-auto">
                    <JsonTreeView data={filteredData} />
                </CardContent>
            )}
        </Card>
    );
};
