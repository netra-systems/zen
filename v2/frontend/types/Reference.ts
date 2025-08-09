export interface ReferenceItem {
    id: number;
    name: string;
    friendly_name: string;
    description?: string | null;
    type: string;
    value: string;
    version: string;
}
