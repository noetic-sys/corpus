/**
 * Formats question text for display by replacing document placeholders with cleaner symbols.
 *
 * Replacements:
 * - @{{LEFT}} → ${{A}}
 * - @{{RIGHT}} → ${{B}}
 * - @{{DOCUMENT}} → ${{D}}
 */
export function formatQuestionTextForDisplay(questionText: string): string {
  return questionText
    .replace(/@\{\{LEFT\}\}/g, '${{A}}')
    .replace(/@\{\{RIGHT\}\}/g, '${{B}}')
    .replace(/@\{\{DOCUMENT\}\}/g, '${{D}}')
}
