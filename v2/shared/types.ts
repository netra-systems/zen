
export interface User {
    id: string;
    full_name?: string;
    email: string;
    picture?: string;
    is_active: boolean;
    is_superuser: boolean;
}

export interface WebSocketMessage {
    event: string;
    data: any;
    run_id: string;
}
