export const MONACO_EDITOR_OPTIONS = {
  minimap: { enabled: false },
  lineNumbers: 'off' as const,
  glyphMargin: false,
  folding: false,
  lineDecorationsWidth: 0,
  lineNumbersMinChars: 0,
  scrollBeyondLastLine: false,
  wordWrap: 'on' as const,
  fontSize: 12,
  fontFamily: 'inherit',
  padding: { top: 12, bottom: 12, left: 12, right: 12 },
  scrollbar: { vertical: 'hidden' as const, horizontal: 'hidden' as const },
  renderLineHighlight: 'none' as const,
  contextmenu: false,
  quickSuggestions: true,
  suggestOnTriggerCharacters: true,
  acceptSuggestionOnEnter: 'on' as const,
  fixedOverflowWidgets: true,
  automaticLayout: true,
  occurrencesHighlight: 'off' as const,
  selectionHighlight: false,
  wordHighlight: false,
  overviewRulerBorder: false,
  hideCursorInOverviewRuler: true,
  overviewRulerLanes: 0
}

export const TEMPLATE_LANGUAGE_CONFIG = {
  id: 'template-text',
  tokenizerRules: {
    root: [
      [/\$\{\{[a-zA-Z_][a-zA-Z0-9_]*\}\}/, 'template-variable']
    ]
  }
}

export const TEMPLATE_THEME_CONFIG = {
  name: 'template-theme',
  base: 'vs' as const,
  inherit: true,
  rules: [
    { token: 'template-variable', foreground: '1e40af', fontStyle: 'bold' }
  ],
  colors: {
    'editor.background': '#ffffff',
    'editorSuggestWidget.border': '#e2e8f0',
    'editorSuggestWidget.background': '#ffffff',
    'editorSuggestWidget.selectedBackground': '#1e40af',
    'editorSuggestWidget.highlightForeground': '#1e40af',
    'editorSuggestWidget.foreground': '#334155'
  }
}