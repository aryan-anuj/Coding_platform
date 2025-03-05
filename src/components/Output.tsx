import { Terminal } from 'lucide-react';

interface OutputProps {
  output: string;
}

export default function Output({ output }: OutputProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="bg-white border-b border-gray-200 p-2 flex items-center">
        <Terminal className="w-4 h-4 mr-2" />
        <span className="text-sm text-gray-500">Output</span>
      </div>
      <div className="flex-grow bg-gray-900 text-gray-100 p-4 font-mono text-sm overflow-auto">
        {output || 'Run your code to see the output here...'}
      </div>
    </div>
  );
}