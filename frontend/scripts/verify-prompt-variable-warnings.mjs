import assert from 'node:assert/strict'
import { pathToFileURL } from 'node:url'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const tempDir = mkdtempSync(join(tmpdir(), 'prompt-variable-warnings-'))

try {
  execFileSync(
    'npx',
    [
      'tsc',
      '--target',
      'ES2022',
      '--module',
      'ES2022',
      '--moduleResolution',
      'bundler',
      '--strict',
      '--skipLibCheck',
      '--outDir',
      tempDir,
      'src/utils/promptVariableWarnings.ts'
    ],
    { cwd: new URL('..', import.meta.url), stdio: 'pipe' }
  )

  const moduleUrl = pathToFileURL(
    join(tempDir, 'promptVariableWarnings.js')
  ).href
  const {
    analyzePromptVariableWarnings,
    buildPromptVariableWarningMessage,
    buildPromptVariableWarningSections,
    extractPromptVariables
  } = await import(`${moduleUrl}?cache=${Date.now()}`)

  assert.deepEqual(extractPromptVariables('请翻译：{text}，第 {{run_index}} 轮'), ['text'])
  assert.deepEqual(extractPromptVariables('JSON 示例：{"name":"Alice"}，变量 {topic}'), ['topic'])

  const singleVersionWarnings = analyzePromptVariableWarnings({
    versions: [{ id: 1, label: 'v1', content: '请翻译：{text}，语气：{tone}' }],
    sampleHeaders: ['text', 'unused'],
    sampleRows: [{ text: '你好', unused: 'x' }, { text: '', unused: 'y' }]
  })
  assert.equal(singleVersionWarnings.length, 3)
  assert.deepEqual(singleVersionWarnings[0], {
    type: 'missing',
    variables: ['tone']
  })
  assert.deepEqual(singleVersionWarnings[1], {
    type: 'extra',
    variables: ['unused']
  })
  assert.deepEqual(singleVersionWarnings[2], {
    type: 'empty',
    variables: ['text'],
    rows: [2]
  })

  const multiVersionWarnings = analyzePromptVariableWarnings({
    versions: [
      { id: 1, label: 'v1', content: '请翻译：{text}' },
      { id: 2, label: 'v2', content: '请翻译：{text}，语气：{tone}' }
    ],
    sampleHeaders: ['text', 'style'],
    sampleRows: [{ text: '你好', style: '正式' }]
  })
  assert.deepEqual(multiVersionWarnings, [
    { type: 'extra', versionLabel: 'v1', variables: ['style'] },
    { type: 'missing', versionLabel: 'v2', variables: ['tone'] },
    { type: 'extra', versionLabel: 'v2', variables: ['style'] }
  ])

  const message = buildPromptVariableWarningMessage(multiVersionWarnings, {
    title: '检测到变量样本风险',
    missingPrefix: '缺少变量',
    extraPrefix: '额外变量',
    emptyPrefix: '空变量值',
    versionPrefix: '版本',
    rowsPrefix: '行',
    continueHint: '仍要继续创建测试任务吗？'
  })
  assert.match(message, /版本 v2：缺少变量 tone/)
  assert.match(message, /版本 v1：额外变量 style/)
  assert.match(message, /仍要继续创建测试任务吗？/)

  const sections = buildPromptVariableWarningSections(multiVersionWarnings, {
    missingPrefix: '缺少变量',
    extraPrefix: '额外变量',
    emptyPrefix: '空变量值',
    versionPrefix: '版本',
    rowsPrefix: '行'
  })
  assert.deepEqual(sections, [
    {
      type: 'extra',
      versionLabel: 'v1',
      prefix: '额外变量',
      variables: ['style']
    },
    {
      type: 'missing',
      versionLabel: 'v2',
      prefix: '缺少变量',
      variables: ['tone']
    },
    {
      type: 'extra',
      versionLabel: 'v2',
      prefix: '额外变量',
      variables: ['style']
    }
  ])
} finally {
  rmSync(tempDir, { recursive: true, force: true })
}
