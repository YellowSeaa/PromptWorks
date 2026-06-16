import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const messagesPath = join(__dirname, '../src/i18n/messages.ts')
const messages = readFileSync(messagesPath, 'utf-8')

assert.match(
  messages,
  /inputSamples:\s+'首行填写变量名，用逗号、分号或 Tab 分隔；后续每行是一组变量值/
)
assert.match(messages, /text,tone\\n你好,正式\\n请介绍 PromptWorks,简洁/)
assert.match(messages, /manualFormat: '手动输入也按 CSV\/TSV 格式解析：首行是变量名/)

assert.match(
  messages,
  /inputSamples:\s+'First row: variable names separated by commas, semicolons, or tabs; each following row is one variable sample/
)
assert.match(messages, /text,tone\\nHello,formal\\nExplain PromptWorks,concise/)
assert.match(
  messages,
  /manualFormat: 'Manual input is parsed as CSV\/TSV: the first row defines variable names/
)

console.log('PASS 新建测试任务手动样本文案明确说明 CSV/TSV 格式')
