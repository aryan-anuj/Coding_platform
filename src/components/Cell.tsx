import React, { useState } from 'react';
import { Cell as CellType } from '../types';
import CodeEditor from './CodeEditor';
import MarkdownCell from './MarkdownCell';
import CellToolbar from './CellToolbar';
import CellOutput from './CellOutput';
import InputCell from './InputCell';  


interface CellProps {
  cell: CellType;
  onUpdate: (id: string, content: string) => void;
  onDelete: (id: string) => void;
  onExecute: (id: string) => void;
  onTypeChange: (id: string, type: 'code' | 'markdown') => void;
}

export default function Cell({ cell, onUpdate, onDelete, onExecute, onTypeChange }: CellProps) {
  const [isEditing, setIsEditing] = useState(cell.type === 'code');
  const [pendingInput, setPendingInput] = useState<string | null>(null); // ✅ Track input state

  const handleUserInput = (userInput: string) => {
    setPendingInput(null); // ✅ Hide input cell after submission
    onExecute(cell.id, userInput); // ✅ Re-run code with user input
  };

  return (
    <div className="border border-gray-200 rounded-lg mb-4 overflow-hidden">
      <CellToolbar
        type={cell.type}
        onTypeChange={(type) => onTypeChange(cell.id, type)}
        onDelete={() => onDelete(cell.id)}
        onExecute={() => cell.type === 'code' && onExecute(cell.id)}
        isExecuting={cell.isExecuting}
      />
      
      <div className="bg-white">
        {cell.type === 'code' ? (
          <CodeEditor
            code={cell.content}
            onChange={(value) => onUpdate(cell.id, value)}
          />
        ) : (
          <MarkdownCell
            content={cell.content}
            isEditing={isEditing}
            onChange={(value) => onUpdate(cell.id, value)}
            onDoubleClick={() => setIsEditing(true)}
            onBlur={() => setIsEditing(false)}
          />
        )}
      </div>

      {/* ✅ Show Input Cell ONLY if the backend detects an input() statement */}
      {cell.requiresInput && !pendingInput && (
        <InputCell prompt={cell.inputPrompt || 'Enter input:'} onSubmit={handleUserInput} />
      )}

      {/* ✅ Show output/errors */}
      {(cell.output || cell.error || cell.images?.length) && (
        <CellOutput output={cell.output} error={cell.error} images={cell.images} />
      )}
    </div>
  );
}





// export default function Cell({ cell, onUpdate, onDelete, onExecute, onTypeChange }: CellProps) {
//   const [isEditing, setIsEditing] = useState(cell.type === 'code');
//   const [pendingInput, setPendingInput] = useState<string | null>(null);

//   const handleUserInput = (userInput: string) => {
//     setPendingInput(null); // ✅ Hide input cell after submission
//     onExecute(cell.id, userInput); // ✅ Re-run code with user input
//   };
  
//   return (
//     <div className="border border-gray-200 rounded-lg mb-4 overflow-hidden">
//       <CellToolbar
//         type={cell.type}
//         onTypeChange={(type) => onTypeChange(cell.id, type)}
//         onDelete={() => onDelete(cell.id)}
//         onExecute={() => cell.type === 'code' && onExecute(cell.id)}
//         isExecuting={cell.isExecuting}
//       />
      
//       <div className="bg-white">
//         {cell.type === 'code' ? (
//           <CodeEditor
//             code={cell.content}
//             onChange={(value) => onUpdate(cell.id, value)}
//           />
//         ) : (
//           <MarkdownCell
//             content={cell.content}
//             isEditing={isEditing}
//             onChange={(value) => onUpdate(cell.id, value)}
//             onDoubleClick={() => setIsEditing(true)}
//             onBlur={() => setIsEditing(false)}
//           />
//         )}
//       </div>

//       {/* {(cell.output || cell.error || cell.images?.length) && (
//         <CellOutput output={cell.output} error={cell.error} images={cell.images} />
//       )}
//     </div> */}
//     {/* ✅ Show Input Cell when backend requests user input */}
//     {cell.requiresInput && !pendingInput && (
//         <InputCell prompt={cell.inputPrompt || 'Enter input:'} onSubmit={handleUserInput} />
//       )}

//       {/* ✅ Show output/errors */}
//       {(cell.output || cell.error || cell.images?.length) && (
//         <CellOutput output={cell.output} error={cell.error} images={cell.images} />
//       )}
//     </div>

//   );
// }
