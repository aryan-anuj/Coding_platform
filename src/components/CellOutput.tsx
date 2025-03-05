interface CellOutputProps {
  output?: string;
  error?: string;
  images?: string[];
  requiresInput?: boolean;
  inputPrompt?: string;
}

export default function CellOutput({ 
  output, 
  error, 
  images, 
  requiresInput = false,  // Default: No input required
  inputPrompt = ""  // Default: Empty prompt
}: CellOutputProps) {
  return (
    <div className="border-t border-gray-200">
      {error && (
        <div className="bg-red-50 p-4 font-mono text-sm text-red-600 whitespace-pre-wrap">
          {error}
        </div>
      )}

      {requiresInput && (
        <div className="bg-yellow-100 p-3 font-mono text-sm text-yellow-700 rounded-md mb-2">
          User input is disabled. Please use predefined variables instead.
        </div>
      )}

      {requiresInput && (
        <div className="bg-yellow-50 p-4 font-mono text-sm text-yellow-600">
          Waiting for user input: {inputPrompt}
        </div>
      )}

      {/* {output && (
        <div className="bg-gray-50 p-4 font-mono text-sm whitespace-pre-wrap">
          {output}
        </div>
      )} */}

      {output && (
        <pre className="font-mono text-sm text-gray-800 whitespace-pre-wrap bg-white p-3 rounded-md">
          {output}
        </pre>
      )}

      
      {images && images.length > 0 && (
        <div className="p-4 bg-white">
          {images.map((image, index) => (
            <img
              key={index}
              src={image}
              alt={`Output ${index + 1}`}
              className="max-w-full h-auto mb-4 last:mb-0"
            />
          ))}
        </div>
      )}
    </div>
  );
}
