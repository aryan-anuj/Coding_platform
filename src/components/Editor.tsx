import { useRef } from 'react';
import Editor from '@monaco-editor/react';
import { Play, Save } from 'lucide-react';

interface CodeEditorProps {
  code: string;
  onChange: (value: string) => void;
  onRun: () => void;
}

export default function CodeEditor({ code, onChange, onRun }: CodeEditorProps) {
  const editorRef = useRef(null);

  const handleEditorDidMount = (editor: any) => {
    editorRef.current = editor;
  };

  return (
    <div className="flex flex-col h-full">
      <div className="bg-white border-b border-gray-200 p-2 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <button
            onClick={onRun}
            className="flex items-center px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
          >
            <Play className="w-4 h-4 mr-1" />
            Run
          </button>
          <button className="flex items-center px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors">
            <Save className="w-4 h-4 mr-1" />
            Save
          </button>
        </div>
        <div className="text-sm text-gray-500">Python Editor</div>
      </div>
      <div className="flex-grow">
        <Editor
          height="100%"
          defaultLanguage="python"
          theme="vs-dark"
          value={code}
          onChange={(value) => onChange(value || '')}
          onMount={handleEditorDidMount}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            rulers: [],
            wordWrap: 'on',
            folding: true,
            scrollBeyondLastLine: false,
            automaticLayout: true,
          }}
        />
      </div>
    </div>
  );
}