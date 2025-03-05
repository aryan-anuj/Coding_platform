import { Code, Type, Trash2, Play, Loader2 } from 'lucide-react';

interface CellToolbarProps {
  type: 'code' | 'markdown';
  onTypeChange: (type: 'code' | 'markdown') => void;
  onDelete: () => void;
  onExecute: () => void;
  isExecuting?: boolean;
}

export default function CellToolbar({ type, onTypeChange, onDelete, onExecute, isExecuting }: CellToolbarProps) {
  return (
    <div className="bg-gray-100 px-4 py-2 flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <button
          onClick={() => onTypeChange('code')}
          className={`p-1 rounded ${type === 'code' ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-200'}`}
          title="Code cell"
        >
          <Code size={16} />
        </button>
        <button
          onClick={() => onTypeChange('markdown')}
          className={`p-1 rounded ${type === 'markdown' ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-200'}`}
          title="Markdown cell"
        >
          <Type size={16} />
        </button>
      </div>
      
      <div className="flex items-center space-x-2">
        {type === 'code' && (
          <button
            onClick={onExecute}
            disabled={isExecuting}
            className={`p-1 rounded ${isExecuting ? 'bg-gray-200' : 'hover:bg-gray-200'}`}
            title="Run cell"
          >
            {isExecuting ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Play size={16} className="text-green-600" />
            )}
          </button>
        )}
        <button
          onClick={onDelete}
          className="p-1 rounded hover:bg-gray-200 text-red-600"
          title="Delete cell"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
}