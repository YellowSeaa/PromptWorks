from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable


@dataclass(frozen=True)
class ProviderDefaults:
    key: str
    name: str
    base_url: str | None
    logo_emoji: str | None
    description: str | None = None
    logo_url: str | None = None


# 预置常见提供方信息，方便前端直接展示品牌内容
_COMMON_PROVIDERS: Dict[str, ProviderDefaults] = {
    "openai": ProviderDefaults(
        key="openai",
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        logo_emoji=None,
        description="通用对话与代码生成能力强，官方模型接入通道。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/openai.svg"
        ),
    ),
    "anthropic": ProviderDefaults(
        key="anthropic",
        name="Anthropic",
        base_url="https://api.anthropic.com",
        logo_emoji=None,
        description="Claude 系列专注长文本与合规场景。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/anthropic.svg"
        ),
    ),
    "azure-openai": ProviderDefaults(
        key="azure-openai",
        name="Azure OpenAI",
        base_url="https://{resource-name}.openai.azure.com",
        logo_emoji=None,
        description="基于 Azure 的企业级 OpenAI 服务，需自定义资源域名。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/azure.svg"
        ),
    ),
    "google": ProviderDefaults(
        key="google",
        name="Google",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        logo_emoji=None,
        description="Gemini 系列涵盖多模态推理与搜索增强。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/google.svg"
        ),
    ),
    "deepseek": ProviderDefaults(
        key="deepseek",
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        logo_emoji=None,
        description="国内团队自研的开源友好模型，突出推理与代码表现。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/deepseek.svg"
        ),
    ),
    "dashscope": ProviderDefaults(
        key="dashscope",
        name="阿里云百炼",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        logo_emoji=None,
        description="通义大模型官方兼容接口，覆盖通用与行业场景。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/qwen.svg"
        ),
    ),
    "siliconflow": ProviderDefaults(
        key="siliconflow",
        name="硅基流动",
        base_url="https://api.siliconflow.cn/v1",
        logo_emoji=None,
        description="专注高性价比推理服务，提供丰富的开源模型托管能力。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/siliconcloud.svg"
        ),
    ),
    "volcengine": ProviderDefaults(
        key="volcengine",
        name="火山引擎 Ark",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        logo_emoji=None,
        description="字节跳动企业级模型平台，支持多模态与大规模并发。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/volcengine.svg"
        ),
    ),
    "ollama": ProviderDefaults(
        key="ollama",
        name="Ollama",
        base_url="http://localhost:11434/v1",
        logo_emoji=None,
        description="本地运行开源模型的 OpenAI 兼容接口，默认连接本机 11434 端口。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/ollama.svg"
        ),
    ),
    "zhipu": ProviderDefaults(
        key="zhipu",
        name="智谱开放平台",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        logo_emoji=None,
        description="GLM 系列专注中文理解与工具调用，生态完整。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/zhipu.svg"
        ),
    ),
    "moonshot": ProviderDefaults(
        key="moonshot",
        name="月之暗面 Moonshot",
        base_url="https://api.moonshot.cn/v1",
        logo_emoji=None,
        description="国内率先开放 128K 以上上下文的高性能大模型。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/moonshot.svg"
        ),
    ),
    "modelscope": ProviderDefaults(
        key="modelscope",
        name="魔搭 ModelScope",
        base_url="https://api-inference.modelscope.cn/v1",
        logo_emoji=None,
        description="阿里云模型社区统一推理入口，便于快速体验模型。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/modelscope.svg"
        ),
    ),
    "qianfan": ProviderDefaults(
        key="qianfan",
        name="百度云千帆",
        base_url="https://qianfan.baidubce.com/v2",
        logo_emoji=None,
        description="百度智能云模型服务，提供文心家族与行业模型接入。",
        logo_url=(
            "https://raw.githubusercontent.com/lobehub/lobe-icons/master/"
            "packages/static-svg/icons/baiducloud.svg"
        ),
    ),
}


def get_provider_defaults(provider_key: str | None) -> ProviderDefaults | None:
    if not provider_key:
        return None
    return _COMMON_PROVIDERS.get(provider_key.lower())


def iter_common_providers() -> Iterable[ProviderDefaults]:
    return _COMMON_PROVIDERS.values()
