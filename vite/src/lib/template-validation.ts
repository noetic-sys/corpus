export interface TemplateValidationResult {
  isValid: boolean
  errors: string[]
  warnings: string[]
}

export function validateTemplateVariables(text: string, availableVariables: string[] = []): TemplateValidationResult {
  const errors: string[] = []

  // Pattern for name-based template variables: ${{variable_name}}
  const namePattern = /\$\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}/g

  // Pattern for ID-based template variables: #{{123}}
  const idPattern = /#\{\{(\d+)\}\}/g

  // Pattern for document placeholder variables: @{{LEFT}}, @{{RIGHT}}
  const docPlaceholderPattern = /@\{\{(LEFT|RIGHT)\}\}/g

  // Find valid template variables (both name and ID based)
  const nameMatches = Array.from(text.matchAll(namePattern))
  const idMatches = Array.from(text.matchAll(idPattern))
  const docPlaceholderMatches = Array.from(text.matchAll(docPlaceholderPattern))

  // Remove valid templates for error checking
  let cleanText = text
  nameMatches.forEach((match, i) => {
    cleanText = cleanText.replace(match[0], `__VALID_NAME_${i}__`)
  })
  idMatches.forEach((match, i) => {
    cleanText = cleanText.replace(match[0], `__VALID_ID_${i}__`)
  })
  docPlaceholderMatches.forEach((match, i) => {
    cleanText = cleanText.replace(match[0], `__VALID_DOC_${i}__`)
  })

  // Check for invalid patterns
  const invalidPatterns = [
    { regex: /\$[a-zA-Z_]/g, msg: (m: string) => `Invalid syntax: "${m}" - use "\${{variable_name}}"` },
    { regex: /\$\{[^}]*$/g, msg: (m: string) => `Incomplete variable: "${m}"` },
    { regex: /\$\{\{[^}]*$/g, msg: (m: string) => `Missing closing braces: "${m}"` },
    { regex: /\{\{[a-zA-Z_#][^}]*\}\}/g, msg: (m: string) => `Missing \$: "${m}"` }
  ]

  invalidPatterns.forEach(({ regex, msg }) => {
    const matches = cleanText.match(regex) || []
    matches.forEach(match => errors.push(msg(match)))
  })

  // Check if name-based variables exist
  if (availableVariables.length > 0 && nameMatches.length > 0) {
    nameMatches.forEach(match => {
      const varName = match[1]
      if (!availableVariables.includes(varName)) {
        errors.push(`Variable "${varName}" not found`)
      }
    })
  }

  // Note: We don't validate ID-based variables as they reference IDs directly

  return { isValid: errors.length === 0, errors, warnings: [] }
}

export function extractTemplateVariableNames(text: string): string[] {
  const validTemplatePattern = /\$\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}/g
  const matches = Array.from(text.matchAll(validTemplatePattern))
  return matches.map(match => match[1])
}

export function extractTemplateVariableIds(text: string): number[] {
  const idPattern = /#\{\{(\d+)\}\}/g
  const matches = Array.from(text.matchAll(idPattern))
  return matches.map(match => parseInt(match[1]))
}

export function extractDocumentPlaceholders(text: string): string[] {
  const docPlaceholderPattern = /@\{\{(LEFT|RIGHT)\}\}/g
  const matches = Array.from(text.matchAll(docPlaceholderPattern))
  return matches.map(match => match[1])
}

export function hasDocumentPlaceholders(text: string): boolean {
  const docPlaceholderPattern = /@\{\{(LEFT|RIGHT)\}\}/g
  return docPlaceholderPattern.test(text)
}