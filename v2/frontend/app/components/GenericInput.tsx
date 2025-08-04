"use client";

import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/card";
import { Button } from "@/components/button";
import Input from "@/components/Input";

interface InputField {
  id: string;
  name: string;
  label: string;
  type: string;
  required: boolean;
  value: string | number;
  onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
}

interface GenericInputProps {
  title: string;
  description: string;
  inputFields: InputField[];
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  isLoading: boolean;
  submitButtonText: string;
  onClear?: () => void;
}

export const GenericInput: React.FC<GenericInputProps> = ({
  title,
  description,
  inputFields,
  onSubmit,
  isLoading,
  submitButtonText,
  onClear,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          {inputFields.map((field) => (
            <div key={field.id}>
              <label htmlFor={field.id} className="block text-sm font-medium text-gray-700">
                {field.label}
              </label>
              <div className="mt-1">
                <Input
                  id={field.id}
                  name={field.name}
                  type={field.type}
                  required={field.required}
                  value={field.value}
                  onChange={field.onChange}
                />
              </div>
            </div>
          ))}
          <div className="flex space-x-2">
            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Loading...' : submitButtonText}
            </Button>
            {onClear && (
              <Button type="button" variant="outline" onClick={onClear}>
                Clear
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
