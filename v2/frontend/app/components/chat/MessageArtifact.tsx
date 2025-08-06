import React, { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Check, Clipboard, Filter, ChevronDown, ChevronUp, X } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuCheckboxItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';

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
        <div style={{ paddingLeft: `${level * 1.5}rem` }} className="space-y-1">
            {entries.map(([key, value]) => (
                <div key={key}>
                    <span className="text-sm font-semibold text-primary mr-2">{key}:</span>
                    <JsonTreeView data={value} level={level + 1} />
                </div>
            ))}
        </div>
    );
};

const getFilterableKeys = (data: any): string[] => {
    const keys = new Set<string>();
    if (typeof data === 'object' && data !== null) {
        Object.keys(data).forEach(key => keys.add(key));
    }
    return Array.from(keys);
};

export const MessageArtifact = ({ data }: MessageArtifactProps) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [isCopied, setIsCopied] = useState(false);

    const allKeys = useMemo(() => getFilterableKeys(data.data), [data]);
    const [filters, setFilters] = useState<Record<string, boolean>>(() => 
        allKeys.reduce((acc, key) => ({ ...acc, [key]: true }), { 'user_query': false })
    );

    const toggleExpand = () => setIsExpanded(!isExpanded);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(JSON.stringify(data, null, 2));
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
    };

    const handleFilterChange = (filter: string) => {
        setFilters(prev => ({ ...prev, [filter]: !prev[filter] }));
    };

    const filteredData = useMemo(() => {
        if (!data.data) return {};
        const filtered = Object.entries(data.data)
            .filter(([key]) => filters[key] !== false)
            .reduce((obj, [key, value]) => ({ ...obj, [key]: value }), {});

        if (filters['user_query'] === false && filtered.input?.messages) {
            delete filtered.input.messages;
        }
        return filtered;
    }, [data, filters]);

    return (
        <Card className="w-full max-w-4xl mx-auto my-2 shadow-md rounded-lg border bg-card">
            <CardHeader className="flex flex-row items-center justify-between p-3 bg-muted/30 rounded-t-lg">
                <Button variant="link" className="p-0 h-auto text-base font-semibold" onClick={toggleExpand}>Agent Event: {data.event}</Button>
                <div className="flex items-center gap-2">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" size="sm">
                                <Filter className="h-4 w-4 mr-2" />
                                Filter
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                            <DropdownMenuCheckboxItem
                                checked={!filters['user_query']}
                                onCheckedChange={() => handleFilterChange('user_query')}
                            >
                                Hide User Query
                            </DropdownMenuCheckboxItem>
                            {allKeys.map(filter => (
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
                    <Button variant="outline" size="sm" onClick={copyToClipboard} title="Copy to clipboard">
                        {isCopied ? <Check className="h-4 w-4 text-green-500" /> : <Clipboard className="h-4 w-4" />}
                    </Button>
                    <Button variant="ghost" size="icon" onClick={toggleExpand} className="h-8 w-8">
                        {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                    </Button>
                </div>
            </CardHeader>
            {isExpanded && (
                <CardContent className="p-4 bg-background/50 rounded-b-lg overflow-x-auto">
                    <JsonTreeView data={filteredData} />
                </CardContent>
            )}
        </Card>
    );
};