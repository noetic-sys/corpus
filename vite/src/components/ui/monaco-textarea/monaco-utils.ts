// eslint-disable-next-line @typescript-eslint/no-unused-vars
import type * as _monacoEditor from 'monaco-editor'
// eslint-disable-next-line @typescript-eslint/no-unused-vars  
import type { Monaco as _Monaco } from '@monaco-editor/react'

export function shouldTriggerTemplateAutocomplete(text: string): boolean {
  return text.endsWith('${{') || /\$\{\{[a-zA-Z_]*$/.test(text)
}

export function convertIdsToNames(
  text: string,
  templateVariables: Array<{ id: number; templateString: string; value: string }>
): string {
  let converted = text

  // First, convert document placeholders: @{{LEFT}} → ${{A}}, @{{RIGHT}} → ${{B}}
  converted = converted.replace(/@\{\{LEFT\}\}/g, '${{A}}')
  converted = converted.replace(/@\{\{RIGHT\}\}/g, '${{B}}')

  // Then convert template variable IDs to names
  templateVariables.forEach(variable => {
    const idPattern = `#{{${variable.id}}}`
    const namePattern = `\${{${variable.templateString}}}`
    converted = converted.replace(
      new RegExp(idPattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'),
      namePattern
    )
  })
  return converted
}

export function convertNamesToIds(
  text: string,
  templateVariables: Array<{ id: number; templateString: string; value: string }>
): string {
  let converted = text

  // First, check for reserved document placeholder names and convert them
  // ${{A}} → @{{LEFT}}, ${{B}} → @{{RIGHT}}
  converted = converted.replace(/\$\{\{A\}\}/g, '@{{LEFT}}')
  converted = converted.replace(/\$\{\{B\}\}/g, '@{{RIGHT}}')

  // Then convert template variable names to IDs (excluding A and B which were already handled)
  templateVariables.forEach(variable => {
    // Skip A and B as they're reserved for document placeholders
    if (variable.templateString === 'A' || variable.templateString === 'B') {
      return
    }

    const namePattern = `\${{${variable.templateString}}}`
    const idPattern = `#{{${variable.id}}}`
    converted = converted.replace(
      new RegExp(namePattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'),
      idPattern
    )
  })
  return converted
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function setupMonacoLanguage(monaco: any, languageId: string, tokenizerRules: any) {
  try {
    console.log(`[MonacoTextarea] Registering ${languageId} language`)
    monaco.languages.register({ id: languageId })
    monaco.languages.setMonarchTokensProvider(languageId, {
      tokenizer: tokenizerRules
    })
  } catch (error) {
    console.error(`[MonacoTextarea] Error registering ${languageId} language:`, error)
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function setupMonacoTheme(monaco: any, themeName: string, themeConfig: any) {
  try {
    monaco.editor.defineTheme(themeName, themeConfig)
    monaco.editor.setTheme(themeName)
  } catch (error) {
    console.error(`[MonacoTextarea] Error setting up theme ${themeName}:`, error)
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function setupAutoResize(editor: any, minHeight: number) {
  const updateHeight = () => {
    const height = Math.max(minHeight, editor.getContentHeight())
    const container = editor.getContainerDomNode()
    if (container) {
      container.style.height = `${height}px`
      const parentContainer = container.parentElement
      if (parentContainer) {
        parentContainer.style.height = `${height}px`
      }
      editor.layout()
    }
  }
  
  editor.onDidContentSizeChange(updateHeight)
  updateHeight()
  
  return updateHeight
}