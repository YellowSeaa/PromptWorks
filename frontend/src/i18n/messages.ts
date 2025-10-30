export const messages = {
  'zh-CN': {
    common: {
      notSet: '未设置',
      cancel: '取消',
      confirm: '确认',
      delete: '删除',
      submit: '提交',
      save: '保存',
      create: '新建',
      edit: '编辑',
      descriptionNone: '暂无描述',
      notEnabled: '未启用'
    },
    app: {
      title: 'PromptWorks 控制台',
      settings: '设置',
      languageCn: '中文',
      languageEn: 'English',
      themeDark: '深色模式'
    },
    menu: {
      prompt: 'Prompt 管理',
      quickTest: '快速测试',
      testJob: '测试任务',
      class: '分类管理',
      tag: '标签管理',
      llm: 'LLMs 管理',
      usage: '用量管理'
    },
    promptManagement: {
      headerTitle: 'Prompt 管理',
      headerDescription: '集中管理提示词资产，快速检索分类、标签与作者信息。',
      createPrompt: '新建 Prompt',
      allClasses: '全部分类',
      searchPlaceholder: '搜索标题 / 内容 / 作者',
      tagPlaceholder: '选择标签筛选',
      sortPlaceholder: '排序方式',
      sortDefault: '默认排序',
      sortCreatedAt: '按创建时间',
      sortUpdatedAt: '按更新时间',
      sortAuthor: '按作者',
      currentVersion: '当前版本',
      author: '作者',
      createdAt: '创建时间',
      updatedAt: '更新时间',
      confirmDelete: '确认删除「{name}」吗？',
      confirm: '确认',
      delete: '删除',
      cancel: '取消',
      emptyDescription: '暂无 Prompt 数据，请点击右上角新建',
      dialogTitle: '新建 Prompt',
      dialogAlert: '当前还没有可用分类，请先在“分类管理”中新增分类。',
      form: {
        title: '标题',
        titlePlaceholder: '请输入 Prompt 标题',
        author: '作者',
        authorPlaceholder: '请输入作者（可选）',
        description: '描述',
        descriptionPlaceholder: '简要说明该 Prompt 的用途',
        class: '所属分类',
        classPlaceholder: '请选择分类',
        tags: '标签',
        tagsPlaceholder: '请选择标签',
        version: '版本号',
        versionPlaceholder: '如 v1.0.0',
        content: '内容',
        contentPlaceholder: '请输入 Prompt 文本内容'
      },
      footer: {
        cancel: '取消',
        submit: '提交'
      },
      messages: {
        missingRequired: '请至少填写标题、版本号和内容',
        selectClass: '请先选择分类',
        createSuccess: '新建 Prompt 成功',
        createFailed: '新建 Prompt 失败',
        deleteSuccess: '已删除「{name}」',
        deleteFailed: '删除 Prompt 失败',
        resourceNotFound: '相关资源不存在',
        loadPromptFailed: '加载 Prompt 列表失败',
        loadCollectionFailed: '加载分类或标签数据失败'
      }
    },
    promptClassManagement: {
      headerTitle: '分类管理',
      headerDescription: '集中维护 Prompt 分类结构，查看各分类下的提示词数量与更新时间。',
      newClass: '新建分类',
      summary: '共 {totalClasses} 个分类 · 覆盖 {totalPrompts} 条 Prompt',
      empty: '暂无分类数据',
      columns: {
        name: '分类名称',
        description: '分类描述',
        promptCount: 'Prompt 数量',
        createdAt: '创建时间',
        latestUpdated: '最近更新',
        actions: '操作'
      },
      delete: '删除',
      dialogTitle: '新建分类',
      form: {
        name: '分类名称',
        namePlaceholder: '请输入分类名称',
        description: '分类描述',
        descriptionPlaceholder: '请输入分类描述（可选）'
      },
      footer: {
        cancel: '取消',
        submit: '提交'
      },
      messages: {
        loadFailed: '加载分类数据失败，请稍后重试',
        nameRequired: '请填写分类名称',
        createSuccess: '分类创建成功',
        createFailed: '创建分类失败，请稍后重试',
        deleteConfirmTitle: '删除确认',
        deleteConfirmMessage: '确认删除分类“{name}”及其关联关系？',
        confirmDelete: '确认删除',
        deleteSuccess: '分类已删除',
        deleteFailed: '删除分类失败，请稍后重试',
        deleteBlocked: '仍有关联 Prompt 使用该分类，请先迁移或删除后再尝试'
      }
    },
    promptTagManagement: {
      headerTitle: '标签管理',
      headerDescription: '维护标签名称与颜色，掌握标签在 Prompt 中的使用频次。',
      newTag: '新建标签',
      summary: '共 {totalTags} 个标签 · 覆盖 {totalPrompts} 条 Prompt',
      empty: '暂无标签数据',
      columns: {
        tag: '标签',
        color: '颜色',
        promptCount: '引用 Prompt 数',
        createdAt: '创建时间',
        updatedAt: '最近更新',
        actions: '操作'
      },
      delete: '删除',
      dialogTitle: '新建标签',
      form: {
        name: '标签名称',
        namePlaceholder: '请输入标签名称',
        color: '标签颜色'
      },
      footer: {
        cancel: '取消',
        submit: '提交'
      },
      messages: {
        loadFailed: '加载标签数据失败，请稍后重试',
        nameRequired: '请填写标签名称',
        createSuccess: '标签创建成功',
        createFailed: '创建标签失败，请稍后重试',
        deleteConfirmTitle: '删除确认',
        deleteConfirmMessage: '确认删除标签“{name}”并解除关联？',
        confirmDelete: '确认删除',
        deleteSuccess: '标签已删除',
        deleteFailed: '删除标签失败，请稍后重试',
        deleteBlocked: '仍有关联 Prompt 使用该标签，请先迁移或删除后再尝试'
      }
    },
    quickTest: {
      headerTitle: '快速测试',
      headerDescription: '针对单个 Prompt 快速发起临时调用，验证模型输出效果。',
      historyPlaceholder: '历史记录',
      newChat: '新建对话',
      sections: {
        model: '模型与参数',
        chat: '对话调试'
      },
      markdown: {
        label: 'Markdown 渲染',
        on: '开',
        off: '关',
        tooltip: '开启后以 Markdown 方式渲染消息内容'
      },
      stream: {
        label: '流式输出',
        on: '开',
        off: '关',
        tooltip: '关闭后将一次性返回完整响应，并记录调用用量'
      },
      form: {
        modelLabel: '模型选择',
        modelPlaceholder: '先选择厂商，再选择模型',
        temperatureLabel: '温度',
        extraParamsLabel: '额外参数',
        extraParamsPlaceholder: '请输入 JSON 格式的模型附加参数'
      },
      chat: {
        empty: '发送首条消息以查看模型响应',
        inputPlaceholder: '在此输入测试内容，支持多行输入',
        promptPlaceholder: '选择历史 Prompt 与版本',
        save: '保存为 Prompt',
        send: '发送',
        tokens: {
          input: '输入 Token',
          output: '输出 Token',
          total: '总计'
        },
        avatar: {
          user: '用户',
          self: '我',
          assistant: '助手',
          system: '系统'
        }
      },
      dialog: {
        title: '保存为 Prompt',
        modeLabel: '保存方式',
        modes: {
          new: '新建 Prompt',
          existing: '追加版本'
        },
        classLabel: '分类',
        classPlaceholder: '选择已有分类',
        nameLabel: '名称',
        namePlaceholder: '请输入 Prompt 名称',
        tagsLabel: '标签',
        tagsPlaceholder: '可选择一个或多个标签',
        versionLabel: '版本标签',
        versionPlaceholderNew: '例如 v1',
        versionPlaceholderExisting: '例如 v2',
        descriptionLabel: '描述',
        descriptionPlaceholder: '可选：补充说明',
        promptLabel: '选择 Prompt',
        promptPlaceholder: '请选择 Prompt',
        contentLabel: '内容',
        actions: {
          cancel: '取消',
          save: '保存'
        }
      },
      session: {
        optionLabel: '{prefix}{title}（{timestamp}）',
        draftPrefix: '草稿·',
        newTitle: '新的对话 {id}',
        historyTitle: '历史对话 {id}'
      },
      messages: {
        draftNotUsed: '当前新建对话尚未使用，请先发送消息',
        extraInvalid: '请输入合法的 JSON 文本',
        extraObjectRequired: '额外参数需为对象结构',
        extraParseFailed: 'JSON 格式解析失败',
        historyLoadFailed: '加载历史记录失败，请稍后再试',
        modelsLoadFailed: '加载模型列表失败，请稍后再试',
        promptsLoadFailed: '加载 Prompt 列表失败，请稍后再试',
        tagsLoadFailed: '加载标签列表失败',
        modelRequired: '请先选择要调用的模型',
        extraFixRequired: '额外参数格式有误，请修正后再发送',
        inputRequired: '请输入要测试的内容',
        requestCancelled: '本次请求已取消',
        invokeFailed: '调用模型失败，请稍后再试',
        saveNoContent: '请输入内容后再保存为 Prompt',
        contentRequired: '内容不能为空',
        nameRequired: '请输入 Prompt 名称',
        createPromptSuccess: '新 Prompt 创建成功',
        selectPromptToUpdate: '请选择要更新的 Prompt',
        versionRequired: '请输入版本标签',
        createPromptVersionSuccess: '已创建新的 Prompt 版本',
        savePromptFailed: '保存 Prompt 失败'
      }
    },
    testJobManagement: {
      headerTitle: '测试任务',
      headerDescription: '统一查看批量测试任务与执行状态，后续将支持任务创建与重跑。',
      createButton: '新建测试任务',
      createButtonNew: '新建测试任务',
      listTitle: '任务列表',
      table: {
        columns: {
          name: '测试名称',
          model: '模型',
          versions: '版本列表',
          temperature: '温度',
          repetitions: '测试次数',
          version: '结果页',
          status: '状态',
          createdAt: '创建时间',
          updatedAt: '最近更新',
          actions: '操作'
        },
        promptPrefix: 'Prompt：',
        notePrefix: '备注：',
        viewDetails: '查看详情',
        retry: '重试',
        delete: '删除',
        version: {
          new: '新版',
          legacy: '旧版'
        }
      },
      versionCount: '{count} 版本',
      empty: '暂未创建测试任务',
      status: {
        completed: '已完成',
        running: '执行中',
        failed: '失败',
        pending: '测试中'
      },
      unnamedPrompt: '未命名 Prompt',
      versionFallback: '版本 #{id}',
      failureReasonPrefix: '失败原因：',
      messages: {
        loadFailed: '加载测试任务失败',
        retrySuccess: '已重新入队失败任务',
        retryFailed: '重试失败，请稍后再试',
        noFailedRuns: '没有需要重试的失败任务',
        deleteConfirmTitle: '确认删除',
        deleteConfirmMessage: '确认删除测试任务「{name}」吗？该操作不可撤销。',
        deleteSuccess: '测试任务已删除',
        deleteFailed: '删除测试任务失败，请稍后再试',
        deleteUnavailable: '当前任务暂不支持删除'
      }
    },
    llmManagement: {
      headerTitle: 'LLMs 管理',
      headerDescription: '统一维护各大模型服务的凭证与接入配置，支撑跨团队的调用治理。',
      addProvider: '新增提供方',
      empty: '暂未接入任何大模型提供方',
      options: {
        customProvider: '自定义提供方'
      },
      card: {
        expand: '展开查看详情',
        collapse: '收起卡片',
        updateApiKey: '更新 API Key',
        deleteProvider: '删除提供方',
        apiKeyLabel: 'API Key（仅展示脱敏信息）',
        baseUrlLabel: '访问地址',
        baseUrlPlaceholderCustom: '请输入自定义 API 域名',
        baseUrlPlaceholderDefault: '官方默认地址自动读取',
        modelsTitle: '已接入模型',
        addModel: '添加模型',
        table: {
          empty: '暂未配置模型',
          columns: {
            name: '模型名称',
            capability: '能力标签',
            quota: '配额策略',
            concurrency: '并发数',
            actions: '操作'
          },
          edit: '编辑',
          check: '检测',
          remove: '删除'
        }
      },
      providerDialog: {
        title: '新增模型提供方',
        providerLabel: '提供方',
        providerPlaceholder: '请选择提供方',
        displayNameLabel: '展示名称',
        displayNamePlaceholder: '请输入提供方名称',
        baseUrlLabel: '接口地址',
        baseUrlPlaceholder: '请输入自定义提供方 API 地址',
        emojiLabel: 'Logo Emoji',
        emojiPlaceholder: '请选择喜欢的 Emoji',
        apiKeyLabel: 'API Key',
        apiKeyPlaceholder: '请输入访问凭证'
      },
      modelDialog: {
        title: '添加模型',
        editTitle: '编辑模型',
        nameLabel: '模型名称',
        namePlaceholder: '请输入模型名称',
        capabilityLabel: '能力标签',
        capabilityPlaceholder: '如 对话 / 推理（可选）',
        quotaLabel: '配额策略',
        quotaPlaceholder: '如 团队共享 100k tokens/日（可选）',
        concurrencyLabel: '测试并发数',
        concurrencyPlaceholder: '并发请求上限，默认 5'
      },
      confirmations: {
        removeModel: {
          title: '提示',
          message: '确认删除该模型接入配置吗？删除后可在后续重新添加。'
        },
        removeProvider: {
          title: '删除确认',
          message: '确认删除提供方“{name}”吗？此操作会同时删除其下的 {count} 个模型配置，且不可恢复。'
        },
        updateApiKey: {
          title: '更新 API Key',
          message: '请输入新的 API Key',
          placeholder: 'sk-...'
        }
      },
      messages: {
        loadProvidersFailed: '加载提供方信息失败，请稍后重试',
        loadCommonProvidersFailed: '加载常用提供方配置失败，仅提供自定义选项',
        providerNameRequired: '请填写提供方名称',
        apiKeyRequired: '请填写 API Key',
        customBaseUrlRequired: '请输入自定义提供方的接口地址',
        createProviderSuccess: '提供方创建成功',
        createProviderFailed: '创建提供方失败，请稍后重试',
        modelRemoved: '模型已移除',
        removeModelFailed: '删除模型失败，请稍后重试',
        modelNameRequired: '请填写模型名称',
        providerNotFound: '未找到对应的提供方，请重新操作',
        createModelSuccess: '模型添加成功',
        createModelFailed: '添加模型失败，请稍后重试',
        updateModelSuccess: '模型配置已更新',
        updateModelFailed: '更新模型失败，请稍后重试',
        concurrencyRequired: '请设置至少 1 的并发数',
        baseUrlUpdated: '访问地址已更新',
        baseUrlUpdateFailed: '更新访问地址失败，请稍后重试',
        providerDeleted: '提供方已删除',
        providerDeleteFailed: '删除提供方失败，请稍后重试',
        invalidApiKey: '请输入有效的 API Key',
        apiKeyUpdated: 'API Key 已更新',
        apiKeyUpdateFailed: '更新 API Key 失败，请稍后重试',
        checkTimeout: '检测超时，请稍后重试',
        checkFailed: '检测失败，请稍后重试',
        checkSuccess: '检测成功，用时 {ms} ms'
      }
    },
    usageManagement: {
      headerTitle: '用量管理',
      headerDescription: '汇总各模型与团队的调用用量，为配额管理和成本分析提供数据支撑。',
      datePicker: {
        rangeSeparator: '至',
        startPlaceholder: '开始日期',
        endPlaceholder: '结束日期',
        shortcuts: {
          last7Days: '最近 7 天',
          last30Days: '最近 30 天'
        }
      },
      overview: {
        cards: {
          totalTokens: '总 Token 数',
          inputTokens: '输入 Token 数',
          outputTokens: '输出 Token 数',
          callCount: '调用次数'
        }
      },
      modelCard: {
        title: '模型用量',
        sortOptions: {
          totalTokens: '按总 Token',
          callCount: '按调用次数',
          inputTokens: '按输入 Token',
          outputTokens: '按输出 Token'
        },
        empty: '暂无用量数据',
        columns: {
          model: '模型',
          totalTokens: '总 Token',
          callCount: '调用次数'
        }
      },
      chart: {
        title: '{model} - Token 趋势',
        defaultModel: '模型用量',
        legend: {
          input: '输入 Token',
          output: '输出 Token'
        },
        stack: '总量'
      },
      messages: {
        usageLoadFailed: '加载用量数据失败，请稍后重试',
        trendLoadFailed: '加载趋势数据失败，请稍后重试'
      }
    },
    promptVersionCreate: {
      breadcrumb: {
        root: 'Prompt 管理',
        fallback: '未命名 Prompt',
        current: '新增版本'
      },
      empty: '未找到 Prompt 信息',
      card: {
        title: '新增版本基础表单',
        subtitle: '提交后可接入后端接口，现阶段用于演示输入结构'
      },
      form: {
        versionLabel: '版本号',
        versionPlaceholder: '例如 v1.5.0',
        summaryLabel: '版本摘要',
        summaryPlaceholder: '简要说明本次更新要点',
        contentLabel: '内容正文',
        contentPlaceholder: '在这里粘贴完整 Prompt 内容',
        referenceLabel: '引用版本',
        referencePlaceholder: '可选择参考版本'
      },
      actions: {
        submit: '提交',
        cancel: '取消'
      },
      messages: {
        promptNotFound: '目标 Prompt 不存在',
        submitFailed: '提交新版本失败',
        idMissing: '无法识别当前 Prompt 编号',
        required: '请填写版本号与内容',
        success: '新增版本成功'
      }
    },
    promptVersionCompare: {
      breadcrumb: {
        root: 'Prompt 管理',
        fallback: '未命名 Prompt',
        current: '版本对比'
      },
      emptyPrompt: '未找到 Prompt 信息',
      card: {
        title: '版本差异对比',
        subtitle: '选择两个不同版本进行比对，左列为基准，右列为对比',
        currentVersion: '当前版本：{version}'
      },
      form: {
        baseLabel: '基准版本',
        basePlaceholder: '请选择基准版本',
        targetLabel: '对比版本',
        targetPlaceholder: '请选择对比版本'
      },
      diff: {
        base: '基准版本',
        target: '对比版本',
        identical: '两个版本内容一致，暂无差异',
        selectTwo: '请选择两个不同的版本进行对比'
      }
    },
    promptDetail: {
      breadcrumb: {
        root: 'Prompt 管理',
        fallback: 'Prompt 详情'
      },
      empty: '未找到 Prompt 详情',
      info: {
        classLabel: '所属分类 · {name}',
        descriptionFallback: '暂无描述',
        currentVersion: '当前版本 {version}',
        currentVersionFallback: '未启用',
        updatedAt: '更新于 {time}',
        fields: {
          author: '作者',
          createdAt: '创建时间',
          updatedAt: '更新时间',
          classDescription: '分类描述',
          classDescriptionFallback: '暂无说明'
        },
        editButton: '编辑分类与标签',
        dialogTitle: '编辑分类与标签',
        dialog: {
          classLabel: '分类',
          classPlaceholder: '请选择分类',
          noClassTip: '暂无分类，请先在“分类管理”中创建',
          tagsLabel: '标签',
          tagsPlaceholder: '选择标签'
        },
        actions: {
          cancel: '取消',
          save: '保存'
        }
      },
      content: {
        title: 'Prompt 内容',
        subtitle: '左侧查看完整内容，右侧切换历史版本',
        newVersion: '新增版本',
        compare: '版本对比',
        versionLabel: '版本号',
        versionFallback: '未选择版本',
        updatedLabel: '更新时间',
        copyTooltip: '复制 Prompt',
        copySuccess: 'Prompt 内容已复制',
        copyFailed: '复制失败，请稍后重试',
        copyEmpty: '当前版本暂无可复制内容',
        empty: '暂无版本内容',
        historyTitle: '历史版本'
      },
      test: {
        title: 'Prompt 测试记录',
        subtitle: '记录历史测试结果，支持快速备案',
        newTest: '新增测试',
        empty: '暂无测试记录，点击右上角新增测试',
        columns: {
          version: 'Prompt 版本',
          model: '模型',
          temperature: '温度',
          repetitions: '测试次数',
          status: '状态',
          createdAt: '发起时间',
          actions: '操作'
        },
        viewResult: '查看结果'
      },
      messages: {
        classRequired: '请选择分类',
        noChange: '分类与标签未发生变化',
        updateSuccess: '分类与标签已更新',
        metaNotFound: '分类或标签数据未找到',
        metaLoadFailed: '加载分类或标签数据失败',
        testLoadFailed: '加载测试记录失败',
        contentEmpty: '暂无内容摘要',
        testUnavailable: '无法打开测试记录，请稍后重试'
      },
      status: {
        completed: '已完成',
        running: '执行中',
        failed: '失败',
        pending: '测试中'
      },
      table: {
        versionFallback: '版本 #{id}'
      }
    },
    testJobResult: {
      breadcrumb: {
        root: '测试任务',
        current: '测试结果'
      },
      empty: '未找到测试任务',
      info: {
        viewPrompt: '查看 Prompt',
        retryButton: '重新执行失败任务',
        failureTitle: '失败原因',
        fields: {
          prompt: '关联 Prompt',
          model: '使用模型',
          repetitionsLabel: '测试次数',
          repetitionsValue: '每个版本 {count} 次',
          temperature: '温度',
          topP: 'Top P',
          createdAt: '创建时间',
          updatedAt: '最近更新'
        },
        descriptionLabel: '任务说明：',
        descriptionFallback: '暂无补充说明',
        extraParams: '模型额外参数'
      },
      resultCard: {
        title: '测试输出对比',
        subtitle: '同模型下对比多个 Prompt 版本的响应表现',
        roundLabel: '第 {current} / {total} 轮',
        updatedAt: '版本更新时间：{time}',
        promptContent: 'Prompt 内容',
        modelOutput: '模型输出',
        tokens: 'Tokens 用量',
        latency: '响应耗时',
        noResult: '当前轮次暂无结果',
        failureTitle: '失败原因'
      },
      analysis: {
        title: '数据分析',
        summary: '平均 Tokens：{tokens}，平均耗时：{latency}',
        columns: {
          version: '版本',
          averageTokens: '平均 Tokens',
          averageLatency: '平均耗时'
        },
        empty: '暂无统计数据'
      },
      summary: {
        promptFallback: '未命名 Prompt',
        defaultTitle: '{prompt} ｜ {model} 对比',
        targetTitle: '{model} ｜ {version}'
      },
      modes: {
        'same-model-different-version': '同模型不同版本',
        'same-version-different-model': '同版本不同模型',
        'multi-turn-same-model': '同版本同模型多轮'
      },
      status: {
        completed: '已完成',
        running: '执行中',
        failed: '失败',
        pending: '测试中'
      },
      messages: {
        loadFailed: '加载测试任务失败',
        noneSelected: '未选择任何测试任务',
        notFound: '未找到测试任务',
        promptContentEmpty: '暂无 Prompt 内容',
        summaryEmpty: '暂无内容',
        retrySuccess: '失败任务已重新排队执行',
        retryFailed: '重试失败，请稍后再试',
        noFailedRuns: '没有可重试的失败任务'
      },
      units: {
        milliseconds: '{value} ms'
      }
    },
    testJobCreate: {
      breadcrumb: {
        promptRoot: 'Prompt 管理',
        testJobRoot: '测试任务',
        current: '新建测试任务'
      },
      card: {
        title: '配置测试模式',
        subtitle: '根据实际需求选择合适的测试策略，后续可挂接真实任务编排'
      },
      modeOptions: {
        'same-model-different-version': {
          label: '同模型不同版本',
          description: '固定模型，对比同一 Prompt 的多个版本，评估版本升级效果。'
        },
        'same-version-different-model': {
          label: '同版本不同模型',
          description: '固定 Prompt 版本，通过多模型对比评估成本与质量差异。'
        },
        'multi-turn-same-model': {
          label: '同版本同模型多轮测试',
          description: '按多轮会话脚本执行稳定性验证，适合客服、助理类场景。'
        }
      },
      form: {
        fields: {
          name: '测试名称',
          namePlaceholder: '例如：v1.4.2 回归测试',
          description: '测试说明',
          descriptionPlaceholder: '补充测试目标、覆盖场景与评估指标',
          prompt: '关联 Prompt',
          promptPlaceholder: '请选择或搜索 Prompt',
          modelForComparison: '对比模型',
          modelPlaceholder: '请选择测试模型',
          versions: '对比版本',
          versionsPlaceholder: '请选择要对比的版本',
          testCount: '测试次数',
          baseVersion: '基准版本',
          baseVersionPlaceholder: '请选择基准版本',
          compareModels: '选择模型',
          compareModelsPlaceholder: '请选择参与对比的模型',
          fixedVersion: '固定版本',
          fixedVersionPlaceholder: '请选择执行版本',
          executeModel: '执行模型',
          executeModelPlaceholder: '请选择用于多轮对话的模型',
          extraParams: '额外参数',
          extraParamsPlaceholder: '请输入 JSON 格式的模型附加参数，例如 { "top_p": 0.8 }',
          temperature: '温度',
          topP: 'Top P'
        },
        tips: {
          noVersions: '暂无可用版本，请先创建 Prompt 版本',
          noVersionsMultiTurn: '暂无版本信息，无法配置多轮测试',
          noModels: '暂无可用模型，请先在“LLMs 配置”中添加模型。',
          testCountHint: '每个版本会按照设定次数重复请求，用于平滑随机波动。',
          noPromptVersions: '当前 Prompt 暂无历史版本，可前往 Prompt 详情补充'
        },
        conversation: {
          title: '多轮对话',
          roundTag: '轮次 {index}',
          addRound: '新增轮次',
          removeRound: '删除',
          roleOptions: {
            system: '系统',
            user: '用户',
            assistant: '助手'
          },
          contentPlaceholder: '填写当前轮次的消息内容'
        },
        actions: {
          create: '创建测试任务',
          back: '返回'
        }
      },
      summary: {
        autoNameSuffix: '测试任务',
        fallbackName: '{prompt} 对比测试'
      },
      messages: {
        keepOneRound: '至少保留一轮对话',
        nameRequired: '请填写测试名称',
        promptRequired: '请选择关联 Prompt',
        promptLoading: '正在加载 Prompt 详情，请稍候',
        promptInvalid: '未获取到有效的 Prompt 信息',
        noModels: '暂无可用模型，请先在“LLMs 配置”中添加',
        selectModels: '请选择需要对比的模型',
        selectTwoVersions: '请至少选择两个 Prompt 版本进行对比',
        testCountMinimum: '测试次数至少为 1 次',
        selectBaseVersion: '请选择基准版本',
        selectAtLeastTwoModels: '请至少选择两个模型参与对比',
        selectVersion: '请选择执行版本',
        selectModel: '请选择执行模型',
        roundContentRequired: '请至少填写一轮对话内容',
        selectComparisonModels: '请选择参与对比的模型',
        noModelsForComparison: '暂无可用模型，请先在“LLMs 配置”中添加模型',
        noModelsForExecution: '暂无可用模型，请先在“LLMs 配置”中添加模型。',
        cancelled: '未创建新的测试任务',
        createSuccess: '测试任务已创建，稍后可在任务列表查看进度',
        createFailed: '创建测试任务失败',
        mockSuccess: '已模拟创建测试任务，可在任务列表中查看（演示）'
      },
      errors: {
        promptList: '加载 Prompt 列表失败',
        llmList: '加载模型配置失败',
        promptDetail: '获取 Prompt 详情失败'
      }
    },
    promptTestCreate: {
      breadcrumb: {
        current: '新建测试任务'
      },
      headerTitle: '新建测试任务',
      headerDescription: '基于 Prompt 测试任务与最小测试单元，快速发起多轮实验。',
      card: {
        title: '测试任务配置',
        subtitle: '配置任务元数据、执行模型与测试样本，提交后可自动触发实验。'
      },
      form: {
        autoExecute: '保存后自动执行',
        sections: {
          task: '任务信息',
          unit: '测试单元配置',
          parameterSets: '参数组合',
          dataset: '测试样本'
        },
        fields: {
          taskName: '任务名称',
          taskDescription: '任务描述',
          prompt: '关联 Prompt',
          promptVersions: '选择版本',
          baseUnitName: '单元命名前缀',
          models: '调用模型',
          parameterSetName: '参数集名称',
          temperature: 'Temperature',
          topP: 'Top P',
          rounds: '执行轮次',
          extraParameters: '附加参数（JSON）',
          inputSamples: '输入样本'
        },
        placeholders: {
          taskName: '请输入任务名称',
          taskDescription: '用于区分或备注的说明信息',
          prompt: '请选择要测试的 Prompt',
          promptVersions: '请选择 Prompt 版本（可多选）',
          baseUnitName: '若不填写，将使用任务名称生成',
          models: '请选择模型提供者与模型（可多选）',
          parameterSetName: '参数集 {index}',
          extraParameters: '如需覆盖 max_tokens、stop 等参数，请输入 JSON 对象',
          inputSamples: '每行一个样本，例如：\n你好\n请介绍 PromptWorks'
        },
        tips: {
          noVersions: '该 Prompt 暂无版本，请先在 Prompt 详情中创建版本。',
          noModels: '暂无可用模型，请先在 LLM 管理中添加模型后再试。',
          rounds: '建议与样本数量保持一致，若不足将循环使用样本。',
          baseUnitName: '用于生成最终单元名称，自动附加模型、版本与参数集信息。',
          samples: '逐行输入样本，执行时按顺序取值；为空则按轮次重复同一提示。',
          csvFormat: '支持 CSV/TXT 文件，首行定义字段名，后续每行为一组变量。',
          noSamples: '暂未导入变量样本，提交后将使用统一提示。',
          variableCount: '当前已解析 {count} 条变量样本。',
          datasetTooltip:
            '若导入变量，总测试次数 = 变量行数 × 执行轮次。当前变量 {rows} 行，执行轮次 {rounds} 次，预计每个模型执行 {total} 次；未导入变量时按轮次重复统一提示。',
          combinationCount: '将生成 {count} 个最小测试单元，提交后可在列表中查看。'
        },
        actions: {
          addParameterSet: '新增参数组合',
          removeParameterSet: '移除',
          inputManual: '手动输入',
          inputCsv: '导入 CSV',
          parseVariables: '解析变量',
          uploadCsv: '上传文件',
          clearVariables: '清空变量'
        },
        defaults: {
          parameterSet: '参数集 {index}'
        },
        submit: '提交任务',
        cancel: '返回列表'
      },
      messages: {
        loadPromptFailed: '加载 Prompt 数据失败，请稍后重试',
        loadProviderFailed: '加载模型数据失败，请稍后重试',
        taskNameRequired: '请填写任务名称',
        promptRequired: '请选择 Prompt 及版本',
        modelRequired: '请选择要调用的模型',
        roundsInvalid: '轮次必须是大于 0 的整数',
        parameterSetRequired: '请至少配置一套参数组合',
        parameterSetRemoveLimit: '至少保留一套参数组合',
        parameterSetJsonInvalid: '参数集「{name}」的 JSON 无效，请检查格式',
        invalidJson: '附加参数必须是合法的 JSON 对象',
        variablesFormatInvalid: '变量格式不正确，首行应为字段名，其余行为取值',
        variablesParsed: '变量样本解析成功，共 {count} 条',
        variablesCleared: '已清空变量样本',
        csvParsed: '已从文件解析 {count} 条变量样本',
        csvParseFailed: '文件格式解析失败，请检查内容',
        csvReadFailed: '文件读取失败，请重试或更换文件',
        noUnits: '未生成任何测试单元，请检查选择的模型、版本与参数集',
        createSuccess: '测试任务创建成功，已提交执行，共生成 {count} 个单元',
        createFailed: '创建测试任务失败，请稍后重试'
      }
    },
    promptTestResult: {
      headerDescription: '创建于 {createdAt} · 状态：{status} · 共 {unitCount} 个最小测试单元',
      headerDescriptionPending: '正在加载测试任务信息...',
      tabs: {
        results: '测试结果',
        units: '最小测试单元',
        analysis: '分析报告'
      },
      breadcrumb: {
        task: '返回任务结果'
      },
      columns: {
        left: '左侧单元',
        right: '右侧单元'
      },
      fields: {
        version: '版本',
        model: '模型',
        parameters: '参数'
      },
      filters: {
        keywordPlaceholder: '搜索单元名称 / 模型 / 版本',
        promptVersion: '筛选版本',
        modelName: '筛选模型',
        parameterSet: '筛选参数集'
      },
      actions: {
        addColumn: '添加列',
        removeColumn: '减少列',
        removeSingleColumn: '移除列',
        columnCount: '当前列数：{count}',
        exportCsv: '导出 CSV'
      },
      markdown: {
        label: 'Markdown 渲染',
        on: '开',
        off: '关',
        tooltip: '开启后以 Markdown 方式展示模型输出'
      },
      labels: {
        outputs: '条结果'
      },
      warnings: {
        missingOutputTitle: 'LLM 响应未能解析结果',
        missingOutputDescription: '模型返回了响应内容，但未提取到可展示的结果，请检查格式或解析规则。',
        viewRawResponse: '查看原始响应'
      },
      dialog: {
        rawResponseTitle: '原始响应 · {unit} · 第 {index} 轮',
        rawResponsePlaceholder: '暂无原始响应内容，可尝试重新执行测试。'
      },
      unitDetail: {
        outputsTitle: '全部结果（共 {count} 条）',
        filteredTitle: '筛选结果（共 {count} 条）',
        parametersTitle: '参数配置（{name}）',
        parametersEmpty: '暂无参数配置信息',
        variableFilterLabel: '变量筛选',
        variableKeyPlaceholder: '选择变量字段',
        variableValuePlaceholder: '输入变量值关键词',
        resetVariableFilter: '重置筛选'
      },
      messages: {
        loadFailed: '加载测试任务结果失败，请稍后重试',
        partialFailed: '部分实验数据加载失败，请稍后重试',
        invalidTask: '无效的测试任务编号',
        invalidUnit: '无效的最小测试单元编号',
        unitLoadFailed: '加载最小测试单元详情失败，请稍后重试'
      },
      fallback: {
        taskTitle: '测试任务 #{id}'
      },
      empty: {
        placeholder: '暂无输出',
        noSelection: '未选择单元',
        noOutputs: '暂无输出结果',
        analysis: '分析报告功能建设中',
        noUnitsFiltered: '暂无符合筛选条件的最小测试单元'
      }
    }
  },
  'en-US': {
    common: {
      notSet: 'Not set',
      cancel: 'Cancel',
      confirm: 'Confirm',
      delete: 'Delete',
      submit: 'Submit',
      save: 'Save',
      create: 'Create',
      edit: 'Edit',
      descriptionNone: 'No description',
      notEnabled: 'Not enabled'
    },
    app: {
      title: 'PromptWorks Console',
      settings: 'Settings',
      languageCn: 'Chinese',
      languageEn: 'English',
      themeDark: 'Dark Mode'
    },
    menu: {
      prompt: 'Prompt Management',
      quickTest: 'Quick Test',
      testJob: 'Test Jobs',
      class: 'Class Management',
      tag: 'Tag Management',
      llm: 'LLM Management',
      usage: 'Usage Management'
    },
    promptManagement: {
      headerTitle: 'Prompt Management',
      headerDescription: 'Manage prompt assets centrally and quickly filter by class, tag, and author.',
      createPrompt: 'New Prompt',
      allClasses: 'All Classes',
      searchPlaceholder: 'Search title / content / author',
      tagPlaceholder: 'Filter by tags',
      sortPlaceholder: 'Sort By',
      sortDefault: 'Default Order',
      sortCreatedAt: 'By Creation Time',
      sortUpdatedAt: 'By Update Time',
      sortAuthor: 'By Author',
      currentVersion: 'Current Version',
      author: 'Author',
      createdAt: 'Created At',
      updatedAt: 'Updated At',
      confirmDelete: 'Delete “{name}”?',
      confirm: 'Confirm',
      delete: 'Delete',
      cancel: 'Cancel',
      emptyDescription: 'No prompt data yet. Click “New Prompt” to create.',
      dialogTitle: 'New Prompt',
      dialogAlert: 'No class available. Please create one under “Class Management”.',
      form: {
        title: 'Title',
        titlePlaceholder: 'Enter prompt title',
        author: 'Author',
        authorPlaceholder: 'Enter author (optional)',
        description: 'Description',
        descriptionPlaceholder: 'Describe the purpose of this prompt',
        class: 'Class',
        classPlaceholder: 'Select a class',
        tags: 'Tags',
        tagsPlaceholder: 'Select tags',
        version: 'Version',
        versionPlaceholder: 'e.g. v1.0.0',
        content: 'Content',
        contentPlaceholder: 'Enter prompt content'
      },
      footer: {
        cancel: 'Cancel',
        submit: 'Submit'
      },
      messages: {
        missingRequired: 'Please fill in title, version, and content.',
        selectClass: 'Please select a class first.',
        createSuccess: 'Prompt created successfully.',
        createFailed: 'Failed to create prompt.',
        deleteSuccess: 'Prompt “{name}” has been deleted.',
        deleteFailed: 'Failed to delete prompt.',
        resourceNotFound: 'Resource not found.',
        loadPromptFailed: 'Failed to load prompt list.',
        loadCollectionFailed: 'Failed to load classes or tags.'
      }
    },
    promptClassManagement: {
      headerTitle: 'Class Management',
      headerDescription: 'Maintain prompt class structures and track prompt counts and updates.',
      newClass: 'New Class',
      summary: '{totalClasses} classes · covering {totalPrompts} prompts',
      empty: 'No class data yet',
      columns: {
        name: 'Class Name',
        description: 'Description',
        promptCount: 'Prompt Count',
        createdAt: 'Created At',
        latestUpdated: 'Last Updated',
        actions: 'Actions'
      },
      delete: 'Delete',
      dialogTitle: 'New Class',
      form: {
        name: 'Class Name',
        namePlaceholder: 'Enter class name',
        description: 'Description',
        descriptionPlaceholder: 'Enter description (optional)'
      },
      footer: {
        cancel: 'Cancel',
        submit: 'Submit'
      },
      messages: {
        loadFailed: 'Failed to load class data. Please try again later.',
        nameRequired: 'Please provide a class name.',
        createSuccess: 'Class created successfully.',
        createFailed: 'Failed to create class. Please try again later.',
        deleteConfirmTitle: 'Delete Confirmation',
        deleteConfirmMessage: 'Delete class “{name}” and its relationships?',
        confirmDelete: 'Delete',
        deleteSuccess: 'Class deleted.',
        deleteFailed: 'Failed to delete class. Please try again later.',
        deleteBlocked: 'Some prompts still use this class. Please migrate or remove them first.'
      }
    },
    promptTagManagement: {
      headerTitle: 'Tag Management',
      headerDescription: 'Manage tag labels and colors, and track their usage across prompts.',
      newTag: 'New Tag',
      summary: '{totalTags} tags · covering {totalPrompts} prompts',
      empty: 'No tag data yet',
      columns: {
        tag: 'Tag',
        color: 'Color',
        promptCount: 'Prompt Count',
        createdAt: 'Created At',
        updatedAt: 'Updated At',
        actions: 'Actions'
      },
      delete: 'Delete',
      dialogTitle: 'New Tag',
      form: {
        name: 'Tag Name',
        namePlaceholder: 'Enter tag name',
        color: 'Tag Color'
      },
      footer: {
        cancel: 'Cancel',
        submit: 'Submit'
      },
      messages: {
        loadFailed: 'Failed to load tag data. Please try again later.',
        nameRequired: 'Please provide a tag name.',
        createSuccess: 'Tag created successfully.',
        createFailed: 'Failed to create tag. Please try again later.',
        deleteConfirmTitle: 'Delete Confirmation',
        deleteConfirmMessage: 'Delete tag “{name}” and detach from prompts?',
        confirmDelete: 'Delete',
        deleteSuccess: 'Tag deleted.',
        deleteFailed: 'Failed to delete tag. Please try again later.',
        deleteBlocked: 'Some prompts still use this tag. Please migrate or remove them first.'
      }
    },
    quickTest: {
      headerTitle: 'Quick Test',
      headerDescription: 'Launch ad-hoc calls for a single prompt to validate model outputs.',
      historyPlaceholder: 'History',
      newChat: 'New Conversation',
      sections: {
        model: 'Model & Parameters',
        chat: 'Conversation Debugging'
      },
      markdown: {
        label: 'Markdown',
        on: 'On',
        off: 'Off',
        tooltip: 'Render messages with Markdown formatting'
      },
      stream: {
        label: 'Streaming',
        on: 'On',
        off: 'Off',
        tooltip: 'Turn off to receive the full response at once and keep usage records'
      },
      form: {
        modelLabel: 'Model Selection',
        modelPlaceholder: 'Pick a provider first, then choose a model',
        temperatureLabel: 'Temperature',
        extraParamsLabel: 'Extra Parameters',
        extraParamsPlaceholder: 'Enter additional parameters in JSON format'
      },
      chat: {
        empty: 'Send the first message to receive a response',
        inputPlaceholder: 'Type test content here. Multi-line is supported.',
        promptPlaceholder: 'Select prompt history and version',
        save: 'Save as Prompt',
        send: 'Send',
        tokens: {
          input: 'Input Tokens',
          output: 'Output Tokens',
          total: 'Total'
        },
        avatar: {
          user: 'User',
          self: 'Me',
          assistant: 'Assistant',
          system: 'System'
        }
      },
      dialog: {
        title: 'Save as Prompt',
        modeLabel: 'Save Mode',
        modes: {
          new: 'Create Prompt',
          existing: 'Append Version'
        },
        classLabel: 'Class',
        classPlaceholder: 'Select an existing class',
        nameLabel: 'Name',
        namePlaceholder: 'Enter prompt name',
        tagsLabel: 'Tags',
        tagsPlaceholder: 'Select one or more tags',
        versionLabel: 'Version Tag',
        versionPlaceholderNew: 'e.g. v1',
        versionPlaceholderExisting: 'e.g. v2',
        descriptionLabel: 'Description',
        descriptionPlaceholder: 'Optional: add extra notes',
        promptLabel: 'Prompt',
        promptPlaceholder: 'Select a prompt',
        contentLabel: 'Content',
        actions: {
          cancel: 'Cancel',
          save: 'Save'
        }
      },
      session: {
        optionLabel: '{prefix}{title} ({timestamp})',
        draftPrefix: 'Draft · ',
        newTitle: 'New conversation {id}',
        historyTitle: 'History conversation {id}'
      },
      messages: {
        draftNotUsed: 'This draft conversation has no activity yet. Send a message first.',
        extraInvalid: 'Enter a valid JSON string.',
        extraObjectRequired: 'Extra parameters must be an object.',
        extraParseFailed: 'Invalid JSON format.',
        historyLoadFailed: 'Failed to load conversation history. Try again later.',
        modelsLoadFailed: 'Failed to load model list. Try again later.',
        promptsLoadFailed: 'Failed to load prompts. Try again later.',
        tagsLoadFailed: 'Failed to load tags.',
        modelRequired: 'Select a model before sending.',
        extraFixRequired: 'Fix extra parameters before sending.',
        inputRequired: 'Enter content to test.',
        requestCancelled: 'Request cancelled.',
        invokeFailed: 'Model invocation failed. Try again later.',
        saveNoContent: 'Enter content before saving as a prompt.',
        contentRequired: 'Content cannot be empty.',
        nameRequired: 'Enter a prompt name.',
        createPromptSuccess: 'Prompt created successfully.',
        selectPromptToUpdate: 'Select a prompt to update.',
        versionRequired: 'Enter a version tag.',
        createPromptVersionSuccess: 'New prompt version created.',
        savePromptFailed: 'Failed to save prompt.'
      }
    },
    testJobManagement: {
      headerTitle: 'Test Jobs',
      headerDescription: 'Review batch test jobs and monitor execution status. Scheduling and re-runs are coming soon.',
      createButton: 'New Test Job',
      createButtonNew: 'New Test Task',
      listTitle: 'Job List',
      table: {
        columns: {
          name: 'Job Name',
          model: 'Model',
          versions: 'Versions',
          temperature: 'Temperature',
          repetitions: 'Runs',
          version: 'Result Page',
          status: 'Status',
          createdAt: 'Created At',
          updatedAt: 'Last Updated',
          actions: 'Actions'
        },
        promptPrefix: 'Prompt: ',
        notePrefix: 'Note: ',
        viewDetails: 'View Details',
        retry: 'Retry',
        delete: 'Delete',
        version: {
          new: 'New',
          legacy: 'Legacy'
        }
      },
      versionCount: '{count} versions',
      empty: 'No test jobs yet',
      status: {
        completed: 'Completed',
        running: 'Running',
        failed: 'Failed',
        pending: 'In Progress'
      },
      unnamedPrompt: 'Untitled Prompt',
      versionFallback: 'Version #{id}',
      failureReasonPrefix: 'Reason:',
      messages: {
        loadFailed: 'Failed to load test jobs.',
        retrySuccess: 'Failed runs re-queued.',
        retryFailed: 'Retry failed. Please try again later.',
        noFailedRuns: 'No failed runs to retry.',
        deleteConfirmTitle: 'Delete Test Job',
        deleteConfirmMessage: 'Delete test job “{name}”? This action cannot be undone.',
        deleteSuccess: 'Test job deleted.',
        deleteFailed: 'Failed to delete test job. Please try again later.',
        deleteUnavailable: 'This job currently cannot be deleted.'
      }
    },
    llmManagement: {
      headerTitle: 'LLM Management',
      headerDescription: 'Manage credentials and integrations for every model provider to support team-wide governance.',
      addProvider: 'Add Provider',
      empty: 'No LLM providers connected yet.',
      options: {
        customProvider: 'Custom Provider'
      },
      card: {
        expand: 'Expand details',
        collapse: 'Collapse card',
        updateApiKey: 'Update API Key',
        deleteProvider: 'Remove provider',
        apiKeyLabel: 'API Key (masked)',
        baseUrlLabel: 'Base URL',
        baseUrlPlaceholderCustom: 'Enter custom API domain',
        baseUrlPlaceholderDefault: 'Using official default endpoint',
        modelsTitle: 'Connected Models',
        addModel: 'Add Model',
        table: {
          empty: 'No models configured',
          columns: {
            name: 'Model Name',
            capability: 'Capability Tags',
            quota: 'Quota Policy',
            concurrency: 'Concurrency',
            actions: 'Actions'
          },
          edit: 'Edit',
          check: 'Check',
          remove: 'Remove'
        }
      },
      providerDialog: {
        title: 'Add Model Provider',
        providerLabel: 'Provider',
        providerPlaceholder: 'Select a provider',
        displayNameLabel: 'Display Name',
        displayNamePlaceholder: 'Enter provider name',
        baseUrlLabel: 'Endpoint',
        baseUrlPlaceholder: 'Enter custom provider API URL',
        emojiLabel: 'Logo Emoji',
        emojiPlaceholder: 'Pick a favorite emoji',
        apiKeyLabel: 'API Key',
        apiKeyPlaceholder: 'Enter access credential'
      },
      modelDialog: {
        title: 'Add Model',
        editTitle: 'Edit Model',
        nameLabel: 'Model Name',
        namePlaceholder: 'Enter model name',
        capabilityLabel: 'Capability Tags',
        capabilityPlaceholder: 'e.g. Chat / Reasoning (optional)',
        quotaLabel: 'Quota Policy',
        quotaPlaceholder: 'e.g. Team shared 100k tokens/day (optional)',
        concurrencyLabel: 'Test Concurrency',
        concurrencyPlaceholder: 'Max concurrent requests (default 5)'
      },
      confirmations: {
        removeModel: {
          title: 'Notice',
          message: 'Remove this model integration? You can reconnect it later.'
        },
        removeProvider: {
          title: 'Delete Provider',
          message: 'Delete provider “{name}”? This removes its {count} model configurations and cannot be undone.'
        },
        updateApiKey: {
          title: 'Update API Key',
          message: 'Enter a new API Key',
          placeholder: 'sk-...'
        }
      },
      messages: {
        loadProvidersFailed: 'Failed to load provider list. Try again later.',
        loadCommonProvidersFailed: 'Failed to load common provider presets; only the custom option is available.',
        providerNameRequired: 'Provide a provider name.',
        apiKeyRequired: 'Enter an API key.',
        customBaseUrlRequired: 'Provide the custom provider endpoint.',
        createProviderSuccess: 'Provider created successfully.',
        createProviderFailed: 'Failed to create provider. Try again later.',
        modelRemoved: 'Model removed.',
        removeModelFailed: 'Failed to remove model. Try again later.',
        modelNameRequired: 'Provide a model name.',
        providerNotFound: 'Provider not found. Please retry.',
        createModelSuccess: 'Model added successfully.',
        createModelFailed: 'Failed to add model. Try again later.',
        updateModelSuccess: 'Model settings updated.',
        updateModelFailed: 'Failed to update model. Try again later.',
        concurrencyRequired: 'Set concurrency to at least 1.',
        baseUrlUpdated: 'Endpoint updated.',
        baseUrlUpdateFailed: 'Failed to update endpoint. Try again later.',
        providerDeleted: 'Provider deleted.',
        providerDeleteFailed: 'Failed to delete provider. Try again later.',
        invalidApiKey: 'Enter a valid API key.',
        apiKeyUpdated: 'API key updated.',
        apiKeyUpdateFailed: 'Failed to update API key. Try again later.',
        checkTimeout: 'Check timed out. Try again later.',
        checkFailed: 'Model check failed. Try again later.',
        checkSuccess: 'Check succeeded in {ms} ms.'
      }
    },
    usageManagement: {
      headerTitle: 'Usage Management',
      headerDescription: 'Aggregate model and team usage to support quota management and cost analysis.',
      datePicker: {
        rangeSeparator: 'to',
        startPlaceholder: 'Start date',
        endPlaceholder: 'End date',
        shortcuts: {
          last7Days: 'Last 7 days',
          last30Days: 'Last 30 days'
        }
      },
      overview: {
        cards: {
          totalTokens: 'Total Tokens',
          inputTokens: 'Input Tokens',
          outputTokens: 'Output Tokens',
          callCount: 'Call Count'
        }
      },
      modelCard: {
        title: 'Model Usage',
        sortOptions: {
          totalTokens: 'Sort by total tokens',
          callCount: 'Sort by call count',
          inputTokens: 'Sort by input tokens',
          outputTokens: 'Sort by output tokens'
        },
        empty: 'No usage data available',
        columns: {
          model: 'Model',
          totalTokens: 'Total Tokens',
          callCount: 'Call Count'
        }
      },
      chart: {
        title: '{model} - Token Trend',
        defaultModel: 'Model Usage',
        legend: {
          input: 'Input Tokens',
          output: 'Output Tokens'
        },
        stack: 'Total'
      },
      messages: {
        usageLoadFailed: 'Failed to load usage data. Try again later.',
        trendLoadFailed: 'Failed to load trend data. Try again later.'
      }
    },
    promptVersionCreate: {
      breadcrumb: {
        root: 'Prompt Management',
        fallback: 'Untitled Prompt',
        current: 'New Version'
      },
      empty: 'Prompt not found.',
      card: {
        title: 'New Version Form',
        subtitle: 'Submit to integrate with backend services. Currently used to demonstrate the payload structure.'
      },
      form: {
        versionLabel: 'Version',
        versionPlaceholder: 'e.g. v1.5.0',
        summaryLabel: 'Summary',
        summaryPlaceholder: 'Briefly describe what changed in this version',
        contentLabel: 'Content',
        contentPlaceholder: 'Paste the full prompt content here',
        referenceLabel: 'Reference Version',
        referencePlaceholder: 'Optional: choose a version to reference'
      },
      actions: {
        submit: 'Submit',
        cancel: 'Cancel'
      },
      messages: {
        promptNotFound: 'Target prompt was not found.',
        submitFailed: 'Failed to submit the new version.',
        idMissing: 'Prompt identifier is invalid.',
        required: 'Please provide the version label and content.',
        success: 'Version created successfully.'
      }
    },
    promptVersionCompare: {
      breadcrumb: {
        root: 'Prompt Management',
        fallback: 'Untitled Prompt',
        current: 'Version Comparison'
      },
      emptyPrompt: 'Prompt not found.',
      card: {
        title: 'Version Diff Comparison',
        subtitle: 'Select two versions to compare. The left column is the baseline, the right column the target.',
        currentVersion: 'Current version: {version}'
      },
      form: {
        baseLabel: 'Baseline',
        basePlaceholder: 'Choose a baseline version',
        targetLabel: 'Target',
        targetPlaceholder: 'Choose a target version'
      },
      diff: {
        base: 'Baseline',
        target: 'Target',
        identical: 'The two versions are identical. No differences found.',
        selectTwo: 'Select two different versions to compare.'
      }
    },
    promptDetail: {
      breadcrumb: {
        root: 'Prompt Management',
        fallback: 'Prompt Detail'
      },
      empty: 'Prompt detail unavailable.',
      info: {
        classLabel: 'Category · {name}',
        descriptionFallback: 'No description yet',
        currentVersion: 'Current version {version}',
        currentVersionFallback: 'Not enabled',
        updatedAt: 'Updated on {time}',
        fields: {
          author: 'Author',
          createdAt: 'Created At',
          updatedAt: 'Updated At',
          classDescription: 'Category Description',
          classDescriptionFallback: 'No additional notes'
        },
        editButton: 'Edit category & tags',
        dialogTitle: 'Edit category & tags',
        dialog: {
          classLabel: 'Category',
          classPlaceholder: 'Choose a category',
          noClassTip: 'No category available yet. Create one under “Class Management”.',
          tagsLabel: 'Tags',
          tagsPlaceholder: 'Select tags'
        },
        actions: {
          cancel: 'Cancel',
          save: 'Save'
        }
      },
      content: {
        title: 'Prompt Content',
        subtitle: 'Review the full content on the left and browse history on the right.',
        newVersion: 'New Version',
        compare: 'Compare Versions',
        versionLabel: 'Version',
        versionFallback: 'No version selected',
        updatedLabel: 'Updated At',
        copyTooltip: 'Copy prompt',
        copySuccess: 'Prompt content copied.',
        copyFailed: 'Copy failed. Please try again.',
        copyEmpty: 'No content to copy for this version.',
        empty: 'No content for this version yet.',
        historyTitle: 'Version History'
      },
      test: {
        title: 'Prompt Test Records',
        subtitle: 'Track historical test runs for quick reference.',
        newTest: 'New Test',
        empty: 'No test records yet. Click “New Test” to start.',
        columns: {
          version: 'Prompt Version',
          model: 'Model',
          temperature: 'Temperature',
          repetitions: 'Runs',
          status: 'Status',
          createdAt: 'Created At',
          actions: 'Actions'
        },
        viewResult: 'View Result'
      },
      messages: {
        classRequired: 'Select a category first.',
        noChange: 'No changes detected for category or tags.',
        updateSuccess: 'Category and tags updated.',
        metaNotFound: 'Category or tag information not found.',
        metaLoadFailed: 'Failed to load category or tag data.',
        testLoadFailed: 'Failed to load test records.',
        contentEmpty: 'No summary available.',
        testUnavailable: 'Unable to open this test record. Please try again later.'
      },
      status: {
        completed: 'Completed',
        running: 'Running',
        failed: 'Failed',
        pending: 'In Progress'
      },
      table: {
        versionFallback: 'Version #{id}'
      }
    },
    testJobResult: {
      breadcrumb: {
        root: 'Test Jobs',
        current: 'Test Result'
      },
      empty: 'Test job not found.',
      info: {
        viewPrompt: 'View Prompt',
        retryButton: 'Retry Failed Runs',
        failureTitle: 'Failure Reason',
        fields: {
          prompt: 'Prompt',
          model: 'Model',
          repetitionsLabel: 'Run Count',
          repetitionsValue: '{count} runs per version',
          temperature: 'Temperature',
          topP: 'Top P',
          createdAt: 'Created At',
          updatedAt: 'Last Updated'
        },
        descriptionLabel: 'Description:',
        descriptionFallback: 'No additional notes.',
        extraParams: 'Extra Parameters'
      },
      resultCard: {
        title: 'Output Comparison',
        subtitle: 'Compare prompt versions under the same model.',
        roundLabel: 'Round {current} / {total}',
        updatedAt: 'Updated at {time}',
        promptContent: 'Prompt Content',
        modelOutput: 'Model Output',
        tokens: 'Tokens Used',
        latency: 'Latency',
        noResult: 'No result for this round yet.',
        failureTitle: 'Failure Reason'
      },
      analysis: {
        title: 'Data Analysis',
        summary: 'Average tokens: {tokens}, average latency: {latency}',
        columns: {
          version: 'Version',
          averageTokens: 'Average Tokens',
          averageLatency: 'Average Latency'
        },
        empty: 'No statistics available.'
      },
      summary: {
        promptFallback: 'Untitled Prompt',
        defaultTitle: '{prompt} | {model} comparison',
        targetTitle: '{model} | {version}'
      },
      modes: {
        'same-model-different-version': 'Same model, different versions',
        'same-version-different-model': 'Same version, different models',
        'multi-turn-same-model': 'Multi-turn, same model'
      },
      status: {
        completed: 'Completed',
        running: 'Running',
        failed: 'Failed',
        pending: 'In Progress'
      },
      messages: {
        loadFailed: 'Failed to load test job.',
        noneSelected: 'No test job selected.',
        notFound: 'Test job not found.',
        promptContentEmpty: 'No prompt content.',
        summaryEmpty: 'No content available.',
        retrySuccess: 'Failed runs re-queued.',
        retryFailed: 'Retry failed. Please try again later.',
        noFailedRuns: 'No failed runs to retry.'
      },
      units: {
        milliseconds: '{value} ms'
      }
    },
    testJobCreate: {
      breadcrumb: {
        promptRoot: 'Prompt Management',
        testJobRoot: 'Test Jobs',
        current: 'New Test Job'
      },
      card: {
        title: 'Configure Test Mode',
        subtitle: 'Choose the right strategy for your evaluation. Workflow orchestration can be integrated later.'
      },
      modeOptions: {
        'same-model-different-version': {
          label: 'Same model, different versions',
          description: 'Fix the model and compare multiple versions of the same prompt to evaluate upgrades.'
        },
        'same-version-different-model': {
          label: 'Same version, different models',
          description: 'Fix a prompt version and compare multiple models to balance quality and cost.'
        },
        'multi-turn-same-model': {
          label: 'Multi-turn with same model',
          description: 'Run scripted conversations to validate stability for assistant-style scenarios.'
        }
      },
      form: {
        fields: {
          name: 'Test Name',
          namePlaceholder: 'e.g. Regression test for v1.4.2',
          description: 'Test Description',
          descriptionPlaceholder: 'Document targets, coverage, and evaluation criteria.',
          prompt: 'Linked Prompt',
          promptPlaceholder: 'Search or select a prompt',
          modelForComparison: 'Comparison Model',
          modelPlaceholder: 'Pick a model for testing',
          versions: 'Comparison Versions',
          versionsPlaceholder: 'Select versions to compare',
          testCount: 'Run Count',
          baseVersion: 'Baseline Version',
          baseVersionPlaceholder: 'Choose a baseline version',
          compareModels: 'Select Models',
          compareModelsPlaceholder: 'Select models to include',
          fixedVersion: 'Fixed Version',
          fixedVersionPlaceholder: 'Choose the execution version',
          executeModel: 'Execution Model',
          executeModelPlaceholder: 'Choose the model for multi-turn conversations',
          extraParams: 'Extra Parameters',
          extraParamsPlaceholder: 'Enter extra parameters in JSON, e.g. { "top_p": 0.8 }',
          temperature: 'Temperature',
          topP: 'Top P'
        },
        tips: {
          noVersions: 'No versions available. Create prompt versions first.',
          noVersionsMultiTurn: 'No version data available. Multi-turn tests cannot be configured.',
          noModels: 'No models available. Please add models under “LLM Management”.',
          testCountHint: 'Each version runs repeatedly to smooth out randomness.',
          noPromptVersions: 'This prompt has no version history yet. Add versions from the prompt detail page.'
        },
        conversation: {
          title: 'Conversation Rounds',
          roundTag: 'Round {index}',
          addRound: 'Add Round',
          removeRound: 'Remove',
          roleOptions: {
            system: 'System',
            user: 'User',
            assistant: 'Assistant'
          },
          contentPlaceholder: 'Enter the message for this round'
        },
        actions: {
          create: 'Create Test Job',
          back: 'Back'
        }
      },
      summary: {
        autoNameSuffix: 'Test Job',
        fallbackName: '{prompt} comparison test'
      },
      messages: {
        keepOneRound: 'Keep at least one conversation round.',
        nameRequired: 'Provide a test name.',
        promptRequired: 'Select a prompt first.',
        promptLoading: 'Prompt detail is still loading. Please wait.',
        promptInvalid: 'Prompt detail is unavailable.',
        noModels: 'No models available. Please add models under “LLM Management”.',
        selectModels: 'Select models to compare.',
        selectTwoVersions: 'Select at least two prompt versions.',
        testCountMinimum: 'Run count must be at least 1.',
        selectBaseVersion: 'Choose a baseline version.',
        selectAtLeastTwoModels: 'Pick at least two models to compare.',
        selectVersion: 'Choose an execution version.',
        selectModel: 'Choose an execution model.',
        roundContentRequired: 'Provide content for at least one round.',
        selectComparisonModels: 'Select models to include in the comparison.',
        noModelsForComparison: 'No models available. Please add models under “LLM Management”.',
        noModelsForExecution: 'No models available. Please add models under “LLM Management”.',
        cancelled: 'No test job was created.',
        createSuccess: 'Test job created. Track progress from the job list.',
        createFailed: 'Failed to create test job.',
        mockSuccess: 'Test job simulated. Review it from the job list.'
      },
      errors: {
        promptList: 'Failed to load prompt list.',
        llmList: 'Failed to load model configurations.',
        promptDetail: 'Failed to fetch prompt detail.'
      }
    },
    promptTestCreate: {
      breadcrumb: {
        current: 'Create Test Task'
      },
      headerTitle: 'Create Test Task',
      headerDescription:
        'Use the new workflow to assemble prompt tests, schedule multiple rounds, and launch experiments quickly.',
      card: {
        title: 'Task Configuration',
        subtitle:
          'Define task metadata, execution model, and sample inputs. Submit the form to run automatically.'
      },
      form: {
        autoExecute: 'Run immediately after save',
        sections: {
          task: 'Task Details',
          unit: 'Test Unit Settings',
          parameterSets: 'Parameter Sets',
          dataset: 'Sample Inputs'
        },
        fields: {
          taskName: 'Task Name',
          taskDescription: 'Description',
          prompt: 'Prompt',
          promptVersions: 'Prompt Versions',
          baseUnitName: 'Unit Name Prefix',
          models: 'Models',
          parameterSetName: 'Parameter Set Name',
          temperature: 'Temperature',
          topP: 'Top P',
          rounds: 'Rounds',
          extraParameters: 'Extra Parameters (JSON)',
          inputSamples: 'Input Samples'
        },
        placeholders: {
          taskName: 'Enter a friendly name for this task',
          taskDescription: 'Optional notes about the scenario',
          prompt: 'Select the prompt to evaluate',
          promptVersions: 'Choose one or more prompt versions',
          baseUnitName: 'Defaults to the task name if left empty',
          models: 'Pick one or more provider models',
          parameterSetName: 'Parameter Set {index}',
          extraParameters: 'Override max_tokens, stop, etc. using a JSON object',
          inputSamples: 'One sample per line, e.g.\nHello\nWhat is PromptWorks?'
        },
        tips: {
          noVersions: 'No versions available. Create a prompt version first.',
          noModels: 'No models found. Add models under LLM Management and retry.',
          rounds: 'Recommended to match the number of samples. Samples loop when rounds exceed inputs.',
          baseUnitName: 'Used to build unit names. Model, version, and parameter set labels will be appended.',
          samples: 'Provide one sample per line. Leave blank to reuse the same prompt for every round.',
          csvFormat: 'CSV/TXT supported. First row defines headers, subsequent rows define variable values.',
          noSamples: 'No variable samples yet. Default prompt will be reused for each round.',
          variableCount: '{count} variable samples parsed.',
          datasetTooltip:
            'When variable samples are provided, total runs = variable rows × execution rounds. Currently {rows} rows and {rounds} rounds, estimated {total} runs per model; without variables the same prompt repeats each round.',
          combinationCount: '{count} minimal test units will be generated.'
        },
        actions: {
          addParameterSet: 'Add Parameter Set',
          removeParameterSet: 'Remove',
          inputManual: 'Manual Input',
          inputCsv: 'Import CSV',
          parseVariables: 'Parse Variables',
          uploadCsv: 'Upload File',
          clearVariables: 'Clear Variables'
        },
        defaults: {
          parameterSet: 'Parameter Set {index}'
        },
        submit: 'Submit Task',
        cancel: 'Back to List'
      },
      messages: {
        loadPromptFailed: 'Failed to load prompt data. Please try again later.',
        loadProviderFailed: 'Failed to load model data. Please try again later.',
        taskNameRequired: 'Task name is required.',
        promptRequired: 'Please select a prompt and version.',
        modelRequired: 'Please select a model.',
        roundsInvalid: 'Rounds must be a positive integer.',
        parameterSetRequired: 'Configure at least one parameter set.',
        parameterSetRemoveLimit: 'Keep at least one parameter set.',
        parameterSetJsonInvalid: 'Invalid JSON in parameter set "{name}". Please review the payload.',
        invalidJson: 'Extra parameters must be valid JSON.',
        variablesFormatInvalid: 'Variable format is invalid. The first row must define headers.',
        variablesParsed: '{count} variable samples parsed successfully.',
        variablesCleared: 'Variable samples cleared.',
        csvParsed: '{count} variable samples imported from file.',
        csvParseFailed: 'Failed to parse the uploaded file. Please verify the format.',
        csvReadFailed: 'Unable to read the file. Please retry or choose another file.',
        noUnits: 'No test units were generated. Please review the selected prompts, models, and parameter sets.',
        createSuccess: 'Test task created and submitted. {count} units scheduled.',
        createFailed: 'Failed to create test task. Please try again later.'
      }
    },
    promptTestResult: {
      headerDescription: 'Created at {createdAt} · Status: {status} · {unitCount} test units',
      headerDescriptionPending: 'Loading test task information...',
      tabs: {
        results: 'Test Results',
        units: 'Test Units',
        analysis: 'Analysis Report'
      },
      breadcrumb: {
        task: 'Back to Task Results'
      },
      columns: {
        left: 'Left Unit',
        right: 'Right Unit'
      },
      fields: {
        version: 'Version',
        model: 'Model',
        parameters: 'Parameters'
      },
      filters: {
        keywordPlaceholder: 'Search unit name / model / version',
        promptVersion: 'Filter Versions',
        modelName: 'Filter Models',
        parameterSet: 'Filter Parameter Sets'
      },
      actions: {
        addColumn: 'Add Column',
        removeColumn: 'Remove Column',
        removeSingleColumn: 'Remove',
        columnCount: 'Columns: {count}',
        exportCsv: 'Export CSV'
      },
      markdown: {
        label: 'Markdown',
        on: 'On',
        off: 'Off',
        tooltip: 'Render model outputs with Markdown formatting'
      },
      labels: {
        outputs: 'outputs'
      },
      warnings: {
        missingOutputTitle: 'LLM response could not be parsed',
        missingOutputDescription: 'The model returned a payload but no displayable result was extracted. Please review the format or parsing rules.',
        viewRawResponse: 'View raw response'
      },
      dialog: {
        rawResponseTitle: 'Raw Response · {unit} · Run #{index}',
        rawResponsePlaceholder: 'Raw response is unavailable. Please retry the test.'
      },
      unitDetail: {
        outputsTitle: 'All Outputs ({count})',
        filteredTitle: 'Filtered Outputs ({count})',
        parametersTitle: 'Parameter Configuration ({name})',
        parametersEmpty: 'No parameter configuration available',
        variableFilterLabel: 'Variable Filter',
        variableKeyPlaceholder: 'Select a variable key',
        variableValuePlaceholder: 'Enter keyword',
        resetVariableFilter: 'Reset'
      },
      messages: {
        loadFailed: 'Failed to load test task results. Please try again later.',
        partialFailed: 'Some experiment data could not be loaded. Please retry later.',
        invalidTask: 'Invalid test task id.',
        invalidUnit: 'Invalid test unit id.',
        unitLoadFailed: 'Failed to load test unit details. Please try again later.'
      },
      fallback: {
        taskTitle: 'Test Task #{id}'
      },
      empty: {
        placeholder: 'No output',
        noSelection: 'No unit selected',
        noOutputs: 'No output data available',
        analysis: 'Analysis report coming soon',
        noUnitsFiltered: 'No test units match the current filters'
      }
    }
  }
} as const

export type SupportedLocale = keyof typeof messages
