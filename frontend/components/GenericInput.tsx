import React, { FormEvent, useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface GenericInputProps {
    title: string;
    description?: string;
    inputFields: Array<{
        name: string;
        label: string;
        type: 'text' | 'number' | 'select';
        placeholder?: string;
        required?: boolean;
        defaultValue?: string | number;
        options?: Array<{ value: string; label: string }>;
    }>;
    onSubmit: (data: Record<string, string | number>) => void;
    isLoading?: boolean;
    submitButtonText?: string;
    onClear?: () => void;
}

type FormState = Record<string, string | number>;

export function GenericInput({ title, description, inputFields, onSubmit, isLoading, submitButtonText, onClear }: GenericInputProps) {
    const [formState, setFormState] = useState<FormState>(() => {
        const initialState: FormState = {};
        inputFields.forEach(field => {
            initialState[field.name] = field.defaultValue ?? '';
        });
        return initialState;
    });

    const handleChange = (name: string, value: string | number) => {
        setFormState(prevState => ({
            ...prevState,
            [name]: value
        }));
    };

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        onSubmit(formState);
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>{title}</CardTitle>
                <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                    {inputFields.map((field) => (
                        <div key={field.name} className="space-y-2">
                            <label htmlFor={field.name} className="text-sm font-medium">{field.label}</label>
                            {field.type === 'select' ? (
                                <Select
                                    name={field.name}
                                    required={field.required}
                                    defaultValue={field.defaultValue as string}
                                    onValueChange={(value) => handleChange(field.name, value)}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder={`Select a ${field.label.toLowerCase()}`} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {field.options?.map((option) => (
                                            <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            ) : (
                                <Input
                                    id={field.name}
                                    name={field.name}
                                    type={field.type}
                                    required={field.required}
                                    value={formState[field.name]}
                                    onChange={(e) => handleChange(field.name, e.target.value)}
                                    className="w-full"
                                />
                            )}
                        </div>
                    ))}
                    <div className="flex justify-end gap-2 pt-4">
                        {onClear && <Button type="button" variant="outline" onClick={onClear}>Clear</Button>}
                        <Button type="submit" disabled={isLoading}>
                            {isLoading ? 'Loading...' : submitButtonText}
                        </Button>
                    </div>
                </form>
            </CardContent>
        </Card>
    );
}