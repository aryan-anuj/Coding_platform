import React, { useState } from 'react';
import { nanoid } from 'nanoid';
import { Cell as CellType } from './types';
import Cell from './components/Cell';
import { PlusCircle } from 'lucide-react';
import { executeCode } from './api';

const DEFAULT_CELLS: CellType[] = [
  {
    id: nanoid(),
    type: 'markdown',
    content: '# Welcome to the Interactive Python Notebook\nTry running the code below!',
  },
  {
    id: nanoid(),
    type: 'code',
    content: ``,
  },
];

function App() {
  const [cells, setCells] = useState<CellType[]>(DEFAULT_CELLS);
  const [executingCellId, setExecutingCellId] = useState<string | null>(null);

  const handleAddCell = (type: 'code' | 'markdown') => {
    const newCell: CellType = {
      id: nanoid(),
      type,
      content: '',
    };
    setCells([...cells, newCell]);
  };

  const handleUpdateCell = (id: string, content: string) => {
    setCells(prevCells =>
      prevCells.map(cell => (cell.id === id ? { ...cell, content } : cell))
    );
  };

  const handleDeleteCell = (id: string) => {
    setCells(prevCells => prevCells.filter(cell => cell.id !== id));
  };

 
  const handleExecuteCell = async (id: string, userInput?: string) => {
    const cell = cells.find(c => c.id === id);
    if (!cell || cell.type !== "code") return;
  
    setExecutingCellId(id);
    setCells(prevCells =>
      prevCells.map(c =>
        c.id === id ? { ...c, isExecuting: true, output: "", error: undefined, images: undefined, requiresInput: false, inputPrompt: "" } : c
      )
    );
  
    try {
      let result = await executeCode(cell.content, userInput);
  
      // ✅ If backend requests input, update state to show InputCell
      if (result.requiresInput) {
        setCells(prevCells =>
          prevCells.map(c =>
            c.id === id ? { ...c, requiresInput: true, inputPrompt: result.inputPrompt } : c
          )
        );
        return;
      }
  
      setCells(prevCells =>
        prevCells.map(c =>
          c.id === id
            ? { ...c, isExecuting: false, output: result.text, error: result.error, images: result.images }
            : c
        )
      );
    } catch (error) {
      setCells(prevCells =>
        prevCells.map(c =>
          c.id === id ? { ...c, isExecuting: false, error: "Failed to execute code" } : c
        )
      );
    }
  
    setExecutingCellId(null);
  };
  
  
  const handleTypeChange = (id: string, type: 'code' | 'markdown') => {
    setCells(prevCells =>
      prevCells.map(cell => (cell.id === id ? { ...cell, type } : cell))
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-semibold text-gray-900">Interactive Python Notebook</h1>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="space-y-6">
          {cells.map(cell => (
            <Cell
              key={cell.id}
              cell={cell}
              onUpdate={handleUpdateCell}
              onDelete={handleDeleteCell}
              onExecute={handleExecuteCell}
              onTypeChange={handleTypeChange}
            />
          ))}
          
          <div className="flex items-center justify-center space-x-4 py-4">
            <button
              onClick={() => handleAddCell('code')}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              <PlusCircle className="w-4 h-4 mr-2" />
              Add Code Cell
            </button>
            <button
              onClick={() => handleAddCell('markdown')}
              className="flex items-center px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
            >
              <PlusCircle className="w-4 h-4 mr-2" />
              Add Markdown Cell
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
