import { shouldTriggerTemplateAutocomplete } from './monaco-utils'
import type * as monacoEditor from 'monaco-editor'
import type { Monaco } from '@monaco-editor/react'

interface TemplateVariable {
  id: number
  templateString: string
  value: string
}

export function createAutocompleteProvider(
  monaco: Monaco,
  templateVariables: TemplateVariable[]
): monacoEditor.IDisposable {
  return monaco.languages.registerCompletionItemProvider('template-text', {
    triggerCharacters: ['{'],

    provideCompletionItems(model: monacoEditor.editor.ITextModel, position: monacoEditor.Position) {
      console.log('[MonacoTextarea] provideCompletionItems called')
      try {
        const textUntilPosition = model.getValueInRange({
          startLineNumber: 1,
          startColumn: 1,
          endLineNumber: position.lineNumber,
          endColumn: position.column,
        })

        if (!shouldTriggerTemplateAutocomplete(textUntilPosition)) {
          return { suggestions: [] }
        }

        const word = model.getWordUntilPosition(position)

        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        }

        const suggestions = templateVariables.map((variable) => ({
          label: variable.templateString,
          kind: monaco.languages.CompletionItemKind.Text,
          insertText: `${variable.templateString}}}`,
          detail: variable.value || '',
          documentation: `Value: ${variable.value || '(empty)'}`,
          range: range,
          sortText: variable.templateString,
        }))

        return { suggestions: suggestions }
      } catch (error) {
        console.error('Error in autocomplete provider:', error)
        return { suggestions: [] }
      }
    },
  })
}

export function disposeProvider(provider: monacoEditor.IDisposable | undefined) {
  if (provider && provider.dispose) {
    try {
      provider.dispose()
    } catch (error) {
      console.error('[MonacoTextarea] Error disposing provider:', error)
    }
  }
}