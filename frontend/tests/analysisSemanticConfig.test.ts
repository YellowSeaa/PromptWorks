import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildAnalysisChartOption,
  buildEmbeddingModelOptions,
  buildSemanticAnalysisParameters,
  formatSemanticMetricValue,
  formatSemanticObjective,
  normalizeSemanticAnalysisChart,
  semanticModelKeyFromParameters
} from '../src/utils/analysisSemanticConfig.ts'
import type { LLMProvider } from '../src/types/llm.ts'

const providers: LLMProvider[] = [
  {
    id: 3,
    provider_key: 'ollama',
    provider_name: 'Ollama',
    base_url: 'http://localhost:11434/v1',
    logo_emoji: null,
    logo_url: null,
    is_custom: false,
    is_archived: false,
    default_model_name: null,
    masked_api_key: '',
    created_at: '',
    updated_at: '',
    models: [
      {
        id: 4,
        name: 'nomic-embed-text',
        model_type: 'embedding',
        embedding_api_style: 'openai_compatible',
        embedding_dimensions: 768,
        embedding_batch_size: 16,
        embedding_max_input_tokens: 2048,
        capability: null,
        quota: null,
        concurrency_limit: 5,
        context_length: null,
        cost_currency: 'CNY',
        cost_display_currency: 'CNY',
        cost_exchange_rate: 1,
        cost_pricing_unit: 1000000,
        cost_input_per_unit: 0,
        cost_output_per_unit: 0,
        cost_tiers: null,
        created_at: '',
        updated_at: ''
      },
      {
        id: 5,
        name: 'doubao-chat',
        model_type: 'chat',
        embedding_api_style: null,
        embedding_dimensions: null,
        embedding_batch_size: null,
        embedding_max_input_tokens: null,
        capability: null,
        quota: null,
        concurrency_limit: 5,
        context_length: null,
        cost_currency: 'CNY',
        cost_display_currency: 'CNY',
        cost_exchange_rate: 1,
        cost_pricing_unit: 1000000,
        cost_input_per_unit: null,
        cost_output_per_unit: null,
        cost_tiers: null,
        created_at: '',
        updated_at: ''
      }
    ]
  }
]

describe('analysisSemanticConfig', () => {
  it('只把模型管理中的 embedding 模型转换为下拉选项', () => {
    assert.deepEqual(buildEmbeddingModelOptions(providers), [
      {
        value: '3:4',
        label: 'Ollama / nomic-embed-text',
        providerId: 3,
        providerName: 'Ollama',
        modelId: 4,
        modelName: 'nomic-embed-text'
      }
    ])
  })

  it('把语义分析表单值转换为后端执行参数', () => {
    assert.deepEqual(buildSemanticAnalysisParameters('3:4', 'consistency', 80), {
      embedding_provider_id: 3,
      embedding_model_id: 4,
      objective_override: 'consistency',
      max_samples_per_group: 80
    })
  })

  it('能从已保存的分析参数恢复模型选择值', () => {
    assert.equal(
      semanticModelKeyFromParameters({
        embedding_provider_id: '3',
        embedding_model_id: 4
      }),
      '3:4'
    )
  })

  it('本地化语义目标并限制语义指标小数位', () => {
    const labels = {
      consistency: '一致性',
      diversity: '多样性',
      balanced: '平衡'
    }

    assert.equal(formatSemanticObjective('consistency', labels), '一致性')
    assert.equal(formatSemanticMetricValue(0.911234, 'zh-CN'), '0.911')
    assert.equal(formatSemanticMetricValue(0.02, 'zh-CN'), '0.02')
  })

  it('能把后端 x/y 图表配置转换为 ECharts option', () => {
    const option = buildAnalysisChartOption(
      {
        id: 'mean_pairwise_similarity',
        title: '平均语义相似度',
        type: 'bar',
        x: 'variable_case_hash',
        y: 'mean_pairwise_similarity'
      },
      [
        {
          variable_case_hash: 'abc123',
          mean_pairwise_similarity: 0.911234
        }
      ],
      (value) => formatSemanticMetricValue(value, 'zh-CN')
    )

    assert.deepEqual((option.xAxis as Record<string, unknown>).data, ['abc123'])
    assert.deepEqual(
      ((option.series as Array<Record<string, unknown>>)[0].data),
      [0.911234]
    )
  })

  it('能兼容旧缓存中缺少 x/y/type 的语义图表配置', () => {
    const normalized = normalizeSemanticAnalysisChart(
      {
        id: 'semantic_dispersion',
        title: '语义离散度',
        option: {}
      },
      0
    )

    assert.equal(normalized.type, 'bar')
    assert.equal(normalized.x, 'variable_case_hash')
    assert.equal(normalized.y, 'semantic_dispersion')
  })
})
