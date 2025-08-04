
import React, { FormEvent } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface InputField {
    id: string;
    name: string;
    label: string;
    type: string;
    required?: boolean;
    defaultValue?: string | number;
    value?: string | number;
    onChange?: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
}

interface GenericInputProps {
    title: string;
    description: string;
    inputFields: InputField[];
    onSubmit: (event: FormEvent<HTMLFormElement>) => void;
    isLoading: boolean;
    submitButtonText: string;
    onClear?: () => void;
}

export function GenericInput({ title, description, inputFields, onSubmit, isLoading, submitButtonText, onClear }: GenericInputProps) {
    return (
        <Card>
            <CardHeader>
                <CardTitle>{title}</CardTitle>
                <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={onSubmit} className="space-y-4">
                    {inputFields.map((field) => (
                        <div key={field.id} className="space-y-2">
                            <label htmlFor={field.id} className="text-sm font-medium">{field.label}</label>
                            <Input
                                id={field.id}
                                name={field.name}
                                type={field.type}
                                required={field.required}
                                defaultValue={field.defaultValue}
                                value={field.value}
                                onChange={field.onChange}
                                className="w-full"
                            />
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
