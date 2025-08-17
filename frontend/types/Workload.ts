import { DataSource } from './backend_schema_base';
import { TimeRange } from './TimeRange';

export interface Workload {
    run_id: string;
    query: string;
    data_source: DataSource;
    time_range: TimeRange;
}
