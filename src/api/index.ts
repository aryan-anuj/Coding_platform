import axios from 'axios';
import { CellOutput } from '../types';

const API_URL = 'http://localhost:5000';

export const executeCode = async (code: string): Promise<CellOutput> => {
  try {
    const response = await axios.post(`${API_URL}/execute`, { code });
    return response.data;
  } catch (error: any) {
    return {
      text: '',
      error: error.response?.data?.error || 'Failed to execute code',
    };
  }
};

export const handleInput = async (input: string, executionId: string): Promise<void> => {
  await axios.post(`${API_URL}/input`, { input, executionId });
};