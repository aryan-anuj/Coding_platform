import MDEditor from '@uiw/react-md-editor';

interface MarkdownCellProps {
  content: string;
  isEditing: boolean;
  onChange: (value: string) => void;
  onDoubleClick: () => void;
  onBlur: () => void;
}

export default function MarkdownCell({
  content,
  isEditing,
  onChange,
  onDoubleClick,
  onBlur,
}: MarkdownCellProps) {
  if (isEditing) {
    return (
      <div data-color-mode="light" className="min-h-[2rem]">
        <MDEditor
          value={content}
          onChange={(value) => onChange(value || '')}
          onBlur={onBlur}
          preview="edit"
          textareaProps={{
            placeholder: 'Type markdown here...',
            style: { minHeight: '2rem' }
          }}
          height="auto"
        />
      </div>
    );
  }

  return (
    <div
      onDoubleClick={onDoubleClick}
      className="p-4 prose max-w-none min-h-[2rem]"
      data-color-mode="light"
    >
      <MDEditor.Markdown source={content || 'Double click to edit...'} />
    </div>
  );
}