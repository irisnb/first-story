"""Classification service for module content.

This service implements the classify-api spec:
- Classify content into modules and sections
- Use LLM for classification
- Support context injection
"""

import json
from typing import Optional

from app.models.modules import MODULE_NAMES, MODULE_SECTIONS, ClassificationResult, ClassifyResponse
from app.services.llm_provider import LLMProvider


CLASSIFY_PROMPT_TEMPLATE = """你是一个剧本内容分类助手。你的任务是将用户输入的内容分类到最合适的模块和章节。

## 可用模块和章节：

1. **world** (世界观)
   - 总述：世界观核心设定概述
   - 魔法/技术系统：规则、限制、代价
   - 社会结构：政治、经济、文化
   - 地理：主要地点、环境
   - 时间线锚点：关键日期、年龄关系
   - 细节记录：零散细节累积

2. **characters** (角色)
   - 总述：角色群体概述
   - 主要角色：主角和重要配角
   - 次要角色：次要配角
   - 角色关系：角色之间的关系

3. **plot** (情节)
   - 总述：故事走向概述
   - 主线：主要情节线
   - 支线：次要情节线
   - 关键事件：重要事件

4. **theme** (主题)
   - 总述：主题概述
   - 核心主题：核心主题描述
   - 次要主题：次要主题描述

5. **structure** (结构)
   - 总述：叙事结构概述
   - 幕布结构：三幕/五幕划分
   - 节奏设计：节奏安排
   - 关键转折点：转折点描述

## 当前上下文：

{context}

## 用户内容：

{content}

## 输出格式：

请以 JSON 格式输出分类结果：
```json
{{
  "classifications": [
    {{
      "module": "模块名",
      "section": "章节名",
      "content": "格式化后的内容（简洁明了）",
      "confidence": 0.0-1.0
    }}
  ]
}}
```

如果内容不属于任何模块，返回空数组：
```json
{{"classifications": []}}
```

注意：
1. 内容可能属于多个模块，请列出所有合适的分类
2. confidence 表示分类的确信程度
3. content 字段应该是简洁明了的描述，适合直接追加到文档中
4. 如果内容是确认性回复（如"好的"、"明白了"），返回空数组
"""


class ClassifyService:
    """Service for classifying content into modules."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """Initialize the classify service.

        Args:
            llm_provider: LLM provider for classification (optional)
        """
        self.llm_provider = llm_provider

    def _build_context(
        self,
        world_summary: str = "",
        character_summary: str = "",
        plot_summary: str = "",
    ) -> str:
        """Build context string for classification.

        Args:
            world_summary: Current world summary
            character_summary: Current character summary
            plot_summary: Current plot summary

        Returns:
            Formatted context string
        """
        parts = []

        if world_summary:
            parts.append(f"世界观摘要：{world_summary}")
        if character_summary:
            parts.append(f"角色摘要：{character_summary}")
        if plot_summary:
            parts.append(f"情节摘要：{plot_summary}")

        if parts:
            return "\n".join(parts)
        return "（暂无上下文）"

    async def classify(
        self,
        content: str,
        world_summary: str = "",
        character_summary: str = "",
        plot_summary: str = "",
    ) -> ClassifyResponse:
        """Classify content into modules and sections.

        Args:
            content: User content to classify
            world_summary: Current world summary for context
            character_summary: Current character summary for context
            plot_summary: Current plot summary for context

        Returns:
            ClassifyResponse with classification results
        """
        if not self.llm_provider:
            # No LLM available, return empty
            return ClassifyResponse(classifications=[])

        context = self._build_context(world_summary, character_summary, plot_summary)
        prompt = CLASSIFY_PROMPT_TEMPLATE.format(context=context, content=content)

        try:
            response = await self.llm_provider.generate(prompt)
            return self._parse_response(response)
        except Exception:
            # On error, return empty
            return ClassifyResponse(classifications=[])

    def _parse_response(self, response: str) -> ClassifyResponse:
        """Parse LLM response into ClassifyResponse.

        Args:
            response: Raw LLM response

        Returns:
            Parsed ClassifyResponse
        """
        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                classifications = []
                for item in data.get("classifications", []):
                    module = item.get("module", "")
                    section = item.get("section", "")

                    # Validate module and section
                    if module not in MODULE_NAMES:
                        continue
                    if section not in MODULE_SECTIONS.get(module, []):
                        continue

                    classifications.append(ClassificationResult(
                        module=module,
                        section=section,
                        content=item.get("content", ""),
                        confidence=item.get("confidence", 0.5),
                    ))

                return ClassifyResponse(classifications=classifications)
        except (json.JSONDecodeError, KeyError):
            pass

        return ClassifyResponse(classifications=[])
