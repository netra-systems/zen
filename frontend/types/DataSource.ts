export interface DataSource {
    source_table: string;
    filters?: { [key: string]: any } | null;
}
