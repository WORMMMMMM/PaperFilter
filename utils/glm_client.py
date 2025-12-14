#!/usr/bin/env python3
"""
GLM API 客户端模块
使用智谱GLM-4进行论文相关性分析和筛选
"""

import requests
import json
from typing import List, Dict, Optional
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GLM_API_KEY, GLM_API_URL, GLM_MODEL


class GLMClient:
    """GLM API客户端"""
    
    def __init__(self, api_key: str = None):
        """
        初始化GLM客户端
        
        Args:
            api_key: API密钥，如果不提供则使用配置文件中的
        """
        self.api_key = api_key or GLM_API_KEY
        self.api_url = GLM_API_URL
        self.model = GLM_MODEL
        
    def _call_api(self, messages: List[Dict], temperature: float = 0.7) -> Optional[str]:
        """
        调用GLM API
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            
        Returns:
            API响应文本
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            print(f"GLM API调用失败: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"GLM API响应解析失败: {e}")
            return None
    
    def analyze_relevance(self, query: str, papers: List[Dict], top_k: int = 10) -> List[Dict]:
        """
        分析论文与查询的相关性，返回最相关的论文
        
        Args:
            query: 用户的研究主题/问题
            papers: 论文列表，每个包含title, abstract等
            top_k: 返回前k篇最相关的论文
            
        Returns:
            排序后的论文列表，包含相关性评分和理由
        """
        if not papers:
            return []
        
        # 构建论文摘要列表
        papers_text = ""
        for i, paper in enumerate(papers):
            title = paper.get('title', 'Unknown')
            abstract = paper.get('abstract', '')[:500]  # 限制摘要长度
            papers_text += f"\n[{i+1}] 标题: {title}\n摘要: {abstract}\n"
        
        prompt = f"""你是一个专业的学术研究助手。用户正在研究以下主题：

【研究主题】
{query}

【候选论文列表】
{papers_text}

请分析每篇论文与用户研究主题的相关性，并选出最相关的{min(top_k, len(papers))}篇论文。

请按以下JSON格式返回结果（只返回JSON，不要其他内容）：
{{
    "selected_papers": [
        {{
            "index": 论文编号(1开始),
            "relevance_score": 相关性评分(0-100),
            "reason": "简短说明为什么相关（50字以内）"
        }}
    ]
}}

注意：
1. 按相关性从高到低排序
2. 只选择真正相关的论文，如果相关论文不足{top_k}篇，可以少选
3. relevance_score要根据实际相关程度给出，不要都给高分
"""

        messages = [
            {"role": "system", "content": "你是一个专业的学术研究助手，擅长分析论文与研究主题的相关性。请只返回JSON格式的结果。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self._call_api(messages, temperature=0.3)
        
        if not response:
            # API调用失败，返回原始列表（按顺序取前top_k个）
            return [{"paper": p, "relevance_score": 50, "reason": "未能进行AI分析"} for p in papers[:top_k]]
        
        try:
            # 解析JSON响应
            # 尝试提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
            else:
                raise ValueError("未找到有效的JSON")
            
            selected = result.get("selected_papers", [])
            
            # 构建结果列表
            ranked_papers = []
            for item in selected:
                idx = item.get("index", 1) - 1  # 转换为0-based索引
                if 0 <= idx < len(papers):
                    ranked_papers.append({
                        "paper": papers[idx],
                        "relevance_score": item.get("relevance_score", 50),
                        "reason": item.get("reason", "")
                    })
            
            return ranked_papers
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"解析GLM响应失败: {e}")
            print(f"原始响应: {response[:500]}")
            # 返回原始列表
            return [{"paper": p, "relevance_score": 50, "reason": "解析失败"} for p in papers[:top_k]]
    
    def summarize_research_direction(self, query: str, papers: List[Dict]) -> str:
        """
        根据筛选出的论文，总结研究方向和建议
        
        Args:
            query: 研究主题
            papers: 已筛选的相关论文列表
            
        Returns:
            研究方向总结
        """
        if not papers:
            return "未找到相关论文，无法生成总结。"
        
        papers_text = ""
        for i, item in enumerate(papers):
            paper = item.get("paper", item)
            title = paper.get('title', 'Unknown')
            abstract = paper.get('abstract', '')[:300]
            papers_text += f"\n{i+1}. {title}\n   摘要: {abstract}\n"
        
        prompt = f"""基于以下研究主题和相关论文，请提供一个简洁的研究方向总结：

【研究主题】
{query}

【相关论文】
{papers_text}

请从以下几个方面进行总结（控制在300字以内）：
1. 该领域的主要研究方向
2. 当前热点问题
3. 建议阅读的重点论文及理由
"""

        messages = [
            {"role": "system", "content": "你是一个专业的学术研究助手，擅长总结研究方向和提供学术建议。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self._call_api(messages, temperature=0.7)
        return response if response else "总结生成失败，请稍后重试。"
    
    def generate_search_keywords(self, user_input: str) -> List[str]:
        """
        根据用户输入生成适合arxiv搜索的关键词
        
        Args:
            user_input: 用户描述的研究兴趣
            
        Returns:
            搜索关键词列表
        """
        prompt = f"""用户想要在arXiv上搜索相关论文，他的研究兴趣如下：

"{user_input}"

请生成3-5个适合在arXiv上搜索的英文关键词或短语。
要求：
1. 关键词应该是学术化的英文术语
2. 每个关键词应该简洁精确
3. 考虑不同的表达方式以获得更全面的结果

请只返回JSON格式的结果，格式如下：
{{
    "keywords": ["keyword1", "keyword2", "keyword3"]
}}
"""

        messages = [
            {"role": "system", "content": "你是一个学术搜索助手，擅长生成精确的学术搜索关键词。只返回JSON格式。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self._call_api(messages, temperature=0.5)
        
        if not response:
            # 失败时直接使用用户输入
            return [user_input]
        
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                keywords = result.get("keywords", [user_input])
                return keywords if keywords else [user_input]
        except:
            pass
        
        return [user_input]


# 测试代码
if __name__ == "__main__":
    client = GLMClient()
    
    # 测试关键词生成
    print("测试关键词生成...")
    keywords = client.generate_search_keywords("我想了解机器人抓取和接触丰富的操作")
    print(f"生成的关键词: {keywords}")

