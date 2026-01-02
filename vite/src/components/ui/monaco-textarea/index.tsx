import { useRef, useEffect, forwardRef } from 'react'
import Editor, { useMonaco, type Monaco } from '@monaco-editor/react'
import type * as monacoEditor from 'monaco-editor'
import { cn } from '@/lib/utils'
import { MONACO_EDITOR_OPTIONS, TEMPLATE_LANGUAGE_CONFIG, TEMPLATE_THEME_CONFIG } from './monaco-config'
import { 
  convertIdsToNames, 
  convertNamesToIds, 
  setupMonacoLanguage, 
  setupMonacoTheme, 
  setupAutoResize 
} from './monaco-utils'
import { createAutocompleteProvider, disposeProvider } from './autocomplete-provider'

interface MonacoTextareaProps {
  value: string
  onChange: (value: string | undefined) => void
  placeholder?: string
  disabled?: boolean
  className?: string
  variant?: 'default' | 'blocky'
  onKeyDown?: (e: monacoEditor.IKeyboardEvent) => void
  minHeight?: number
  templateVariables?: Array<{ id: number; templateString: string; value: string }>
}

export const MonacoTextarea = forwardRef<monacoEditor.editor.IStandaloneCodeEditor | null, MonacoTextareaProps>(
  ({ 
    value, 
    onChange,
    disabled = false,
    className = '',
    variant = 'default',
    onKeyDown,
    minHeight = 60,
    templateVariables = []
  }, ref) => {
    const editorRef = useRef<monacoEditor.editor.IStandaloneCodeEditor | null>(null)
    const monaco = useMonaco()

    // Display value with names instead of IDs
    const displayValue = convertIdsToNames(value, templateVariables)

    // Handle onChange to convert back to IDs
    const handleChange = (newValue: string | undefined) => {
      if (newValue !== undefined) {
        const convertedValue = convertNamesToIds(newValue, templateVariables)
        onChange(convertedValue)
      } else {
        onChange(newValue)
      }
    }

    useEffect(() => {
      if (ref) {
        if (typeof ref === 'function') {
          ref(editorRef.current)
        } else {
          ref.current = editorRef.current
        }
      }
    }, [ref])

    useEffect(() => {
      if (!monaco || !templateVariables || templateVariables.length === 0) {
        return
      }

      let provider: monacoEditor.IDisposable | undefined
      try {
        provider = createAutocompleteProvider(monaco, templateVariables)
      } catch (error) {
        console.error('[MonacoTextarea] Error registering completion provider:', error)
      }

      return () => disposeProvider(provider)
    }, [monaco, templateVariables])

    const handleEditorDidMount = (editor: monacoEditor.editor.IStandaloneCodeEditor, monaco: Monaco) => {
      editorRef.current = editor

      try {
        // Setup syntax highlighting for template variables
        setupMonacoLanguage(monaco, TEMPLATE_LANGUAGE_CONFIG.id, TEMPLATE_LANGUAGE_CONFIG.tokenizerRules)

        // Setup theme
        setupMonacoTheme(monaco, TEMPLATE_THEME_CONFIG.name, TEMPLATE_THEME_CONFIG)

        // Keyboard events
        if (onKeyDown) {
          editor.onKeyDown(onKeyDown)
        }

        // Auto-resize
        setupAutoResize(editor, minHeight)
      } catch (error) {
        console.error('[MonacoTextarea] Error setting up Monaco editor:', error)
        console.error('[MonacoTextarea] Error stack:', error instanceof Error ? error.stack : 'No stack trace available')
      }
    }

    // Cleanup on unmount
    useEffect(() => {
      return () => {
        if (editorRef.current) {
          try {
            editorRef.current.dispose()
          } catch (error) {
            console.error('[MonacoTextarea] Error disposing editor:', error)
          }
        }
      }
    }, [])

    const containerClasses = cn(
      'overflow-visible rounded-md border border-input bg-background text-sm ring-offset-background relative',
      'transition-all duration-200',
      variant === 'default' && 'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2',
      variant === 'blocky' && [
        'rounded-none border-2 border-black bg-white'
      ],
      disabled && 'cursor-not-allowed opacity-50',
      className
    )

    return (
      <div className={containerClasses}>
        <Editor
          height={minHeight}
          language="template-text"
          value={displayValue}
          onChange={handleChange}
          onMount={handleEditorDidMount}
          options={{
            ...MONACO_EDITOR_OPTIONS,
            readOnly: disabled
          }}
        />
      </div>
    )
  }
)

MonacoTextarea.displayName = 'MonacoTextarea'