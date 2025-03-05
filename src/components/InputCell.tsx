import { useState } from 'react';

interface InputCellProps {
  prompt: string;
  onSubmit: (input: string) => void;
}

export default function InputCell({ prompt, onSubmit }: InputCellProps) {
  const [userInput, setUserInput] = useState('');

  const handleSubmit = () => {
    if (userInput.trim() !== '') {
      onSubmit(userInput); // ✅ Send input to backend
      setUserInput(''); // ✅ Clear input after submission
    }
  };

  return (
    <div className="border-t border-gray-200 bg-yellow-50 p-4">
      <p className="font-mono text-sm text-yellow-600">{prompt}</p>
      <input
        type="text"
        value={userInput}
        onChange={(e) => setUserInput(e.target.value)}
        className="mt-2 w-full p-2 border rounded text-sm"
        placeholder="Enter input..."
      />
      <button
        onClick={handleSubmit}
        className="mt-2 px-4 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Submit
      </button>
    </div>
  );
}
