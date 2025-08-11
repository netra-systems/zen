import { DataSource } from './DataSource';
import { TimeRange } from './TimeRange';

export interface Workload {
    run_id: string;
    query: string;
    data_source: DataSource;
    time_range: TimeRange;
}
