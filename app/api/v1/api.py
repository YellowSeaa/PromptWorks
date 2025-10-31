from fastapi import APIRouter

from app.api.v1.endpoints import (
    llms,
    prompt_classes,
    prompt_tags,
    prompts,
    test_prompt,
    usage,
    prompt_test_tasks,
    settings,
)


api_router = APIRouter()
api_router.include_router(llms.router, prefix="/llm-providers", tags=["llm_providers"])
api_router.include_router(
    prompt_classes.router, prefix="/prompt-classes", tags=["prompt_classes"]
)
api_router.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
api_router.include_router(
    prompt_tags.router, prefix="/prompt-tags", tags=["prompt_tags"]
)
api_router.include_router(
    test_prompt.router, prefix="/test_prompt", tags=["test_prompt"]
)
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
api_router.include_router(prompt_test_tasks.router)
api_router.include_router(settings.router)
