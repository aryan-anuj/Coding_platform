export interface Cell {
  id: string;
  type: 'code' | 'markdown';
  content: string;
  output?: string;
  isExecuting?: boolean;
  error?: string;
  images?: string[];
}

export interface CellOutput {
  text: string;
  error?: string;
  images?: string[];
  needsInput?: boolean;
  inputPrompt?: string;
}