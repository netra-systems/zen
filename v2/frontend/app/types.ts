
export interface Message {
  role: 'user' | 'assistant';
  content: string;
  artifact?: Artifact;
}

export interface Artifact {
  type: 'table' | 'chart' | 'code';
  data: any;
}

export interface User {
    id: number;
    full_name?: string;
    email: string;
    picture?: string;
}
