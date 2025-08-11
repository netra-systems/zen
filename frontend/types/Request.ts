import { Workload } from './Workload';

export interface RequestModel {
    id?: string;
    user_id: string;
    query: string;
    workloads: Workload[];
    constraints?: any;
}
