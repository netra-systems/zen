export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
}

export interface User {
    id: number;
    full_name?: string;
    email: string;
    picture?: string;
}