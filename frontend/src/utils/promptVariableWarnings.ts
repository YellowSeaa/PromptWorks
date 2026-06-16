export interface PromptVariableVersion {
  id: number
  label: string
  content: string
}

export type PromptVariableWarningType = 'missing' | 'extra' | 'empty'

export interface PromptVariableWarning {
  type: PromptVariableWarningType
  versionLabel?: string
  variables: string[]
  rows?: number[]
}

export interface PromptVariableWarningLabels {
  title: string
  missingPrefix: string
  extraPrefix: string
  emptyPrefix: string
  versionPrefix: string
  rowsPrefix: string
  continueHint: string
}

export type PromptVariableWarningSectionLabels = Pick<
  PromptVariableWarningLabels,
  'missingPrefix' | 'extraPrefix' | 'emptyPrefix' | 'versionPrefix' | 'rowsPrefix'
>

export interface PromptVariableWarningSection {
  type: PromptVariableWarningType
  versionLabel?: string
  prefix: string
  variables: string[]
  rows?: number[]
}

const VARIABLE_PATTERN = /\{([A-Za-z_][A-Za-z0-9_]*)\}/g
const SYSTEM_VARIABLES = new Set(['run_index'])

export function extractPromptVariables(content: string): string[] {
  const variables = new Set<string>()
  for (const match of content.matchAll(VARIABLE_PATTERN)) {
    const name = match[1]
    const start = match.index ?? 0
    if (
      SYSTEM_VARIABLES.has(name) ||
      content[start - 1] === '{' ||
      content[start + match[0].length] === '}' ||
      looksLikeJsonProperty(content, start, match[0].length)
    ) {
      continue
    }
    variables.add(name)
  }
  return [...variables].sort((a, b) => a.localeCompare(b))
}

export function analyzePromptVariableWarnings({
  versions,
  sampleHeaders,
  sampleRows
}: {
  versions: PromptVariableVersion[]
  sampleHeaders: string[]
  sampleRows: Array<Record<string, string>>
}): PromptVariableWarning[] {
  const normalizedHeaders = uniqueSorted(
    sampleHeaders.map((header) => header.trim()).filter(Boolean)
  )
  const headerSet = new Set(normalizedHeaders)
  const includeVersionLabel = versions.length > 1
  const warnings: PromptVariableWarning[] = []

  for (const version of versions) {
    const promptVariables = extractPromptVariables(version.content)
    const promptVariableSet = new Set(promptVariables)
    const versionLabel = includeVersionLabel ? version.label : undefined
    const missing = promptVariables.filter((name) => !headerSet.has(name))
    const extra = normalizedHeaders.filter((name) => !promptVariableSet.has(name))

    if (missing.length) {
      warnings.push(buildWarning('missing', missing, versionLabel))
    }
    if (extra.length) {
      warnings.push(buildWarning('extra', extra, versionLabel))
    }
  }

  const emptyVariables = new Map<string, Set<number>>()
  sampleRows.forEach((row, index) => {
    normalizedHeaders.forEach((header) => {
      if ((row[header] ?? '').trim() !== '') {
        return
      }
      const rows = emptyVariables.get(header) ?? new Set<number>()
      rows.add(index + 1)
      emptyVariables.set(header, rows)
    })
  })

  emptyVariables.forEach((rows, variable) => {
    warnings.push({
      type: 'empty',
      variables: [variable],
      rows: [...rows].sort((a, b) => a - b)
    })
  })

  return warnings
}

export function buildPromptVariableWarningMessage(
  warnings: PromptVariableWarning[],
  labels: PromptVariableWarningLabels
): string {
  const lines = warnings.map((warning) => {
    const scope = warning.versionLabel
      ? `${labels.versionPrefix} ${warning.versionLabel}：`
      : ''
    const variables = warning.variables.join(', ')
    if (warning.type === 'missing') {
      return `${scope}${labels.missingPrefix} ${variables}`
    }
    if (warning.type === 'extra') {
      return `${scope}${labels.extraPrefix} ${variables}`
    }
    const rows = warning.rows?.join(', ') ?? ''
    return `${scope}${labels.emptyPrefix} ${variables} (${labels.rowsPrefix} ${rows})`
  })
  return [labels.title, '', ...lines, '', labels.continueHint].join('\n')
}

export function buildPromptVariableWarningSections(
  warnings: PromptVariableWarning[],
  labels: PromptVariableWarningSectionLabels
): PromptVariableWarningSection[] {
  return warnings.map((warning) => ({
    type: warning.type,
    ...(warning.versionLabel ? { versionLabel: warning.versionLabel } : {}),
    prefix: warningPrefix(warning.type, labels),
    variables: warning.variables,
    ...(warning.rows?.length ? { rows: warning.rows } : {})
  }))
}

function looksLikeJsonProperty(content: string, start: number, length: number): boolean {
  const before = content[start - 1]
  const after = content[start + length]
  const nextNonSpace = content.slice(start + length).match(/\S/)
  return (
    (before === '"' || before === "'") &&
    (after === '"' || after === "'") &&
    nextNonSpace?.[0] === ':'
  )
}

function uniqueSorted(values: string[]): string[] {
  return [...new Set(values)].sort((a, b) => a.localeCompare(b))
}

function buildWarning(
  type: PromptVariableWarningType,
  variables: string[],
  versionLabel?: string
): PromptVariableWarning {
  return versionLabel ? { type, versionLabel, variables } : { type, variables }
}

function warningPrefix(
  type: PromptVariableWarningType,
  labels: PromptVariableWarningSectionLabels
): string {
  if (type === 'missing') return labels.missingPrefix
  if (type === 'extra') return labels.extraPrefix
  return labels.emptyPrefix
}
