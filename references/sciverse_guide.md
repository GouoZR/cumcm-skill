# Sciverse 学术文献检索 — cumcm-skill 集成指南

> Sciverse (穹宇) = 上海人工智能实验室 MinerU 团队的科学数据基座。
> 4.66 亿学术元数据 + 2,800 万 OA 全文 → AI-Ready 结构化数据。
> cumcm-skill v1.0 起集成为默认文献检索后端，确保所有引用可溯源。

---

## 快速接入

### 方式 1: MCP Server (推荐，Claude Code 原生)

```bash
# 1. 获取 API Token: https://sciverse.space/tokens (免费注册)

# 2. 安装 MCP Server
claude mcp add -s user sciverse -- npx -y sciverse-mcp-server

# 3. 设置环境变量
# 将 SCIVERSE_API_TOKEN 添加到环境变量中
```

安装后，在 Claude Code 中可直接调用 Sciverse 的 MCP 工具:
- `semantic_search` — 语义搜索，返回带引用的证据片段
- `search_papers` — 结构化元数据搜索
- `read_content` — 按 doc_id 读原文片段
- `list_paper_relations` — 论文引用关系网络
- `get_resource` — 获取论文图片/表格

### 方式 2: Python SDK (求解代码中使用)

```bash
pip install sciverse
sciverse auth login
```

### 方式 3: REST API (兜底)

```python
import os, httpx
BASE = "https://api.sciverse.space"
HEADERS = {"Authorization": f"Bearer {os.environ['SCIVERSE_API_TOKEN']}"}

r = httpx.post(f"{BASE}/agentic-search", json={
    "query": "NSGA-II multi-objective optimization",
    "top_k": 20
}, headers=HEADERS)
```

---

## 六大 API 速查

| API | MCP 工具名 | 用途 | 数模竞赛场景 |
|------------------------|----------------------|---------------------------------|-----------------------------------|
| **semantic_search** | `semantic_search` | 自然语言 → 带引用的原文证据片段 | ⭐ 最常用: 搜类似题目解法、模型对比 |
| **search_papers** | `search_papers` | 作者/年份/期刊/引用数等结构化筛选 | 找经典文献、高引论文 |
| **list_catalog** | `list_catalog` | 查询可用筛选字段 | 了解能搜什么维度 |
| **list_paper_relations** | `list_paper_relations` | 论文引用关系网络 | 滚雪球检索: 从一篇关键论文扩展开 |
| **read_content** | `read_content` | 按 doc_id + offset 读原文片段 | 核验 semantic_search 返回的证据 |
| **get_resource** | `get_resource` | 获取论文图片/表格 | 查看方法流程图、结果对比表 |

### 典型调用链

```
场景: 搜"物流配送路径优化的最新方法"
  → semantic_search("logistics vehicle routing optimization 2024")
  → 返回带引用的证据 chunks + doc_id
  → 对关键 chunk 调 content(doc_id, offset) 扩展上下文
  → 对感兴趣的方法调 list_paper_relations(doc_id) 找更多相关工作
```

---

## 各阶段集成点

### Stage 0 — 团队启动 + 资料预扫

**用途**: 快速了解题目背景领域，搜相关综述。

| 检索 | Query 示例 |
|----------|---------------------------------|
| 背景调研 | `<题目关键词> survey review 综述` |
| 数学模型 | `<题目关键词> mathematical model` |
| 数据可得性 | `<题目关键词> benchmark dataset` |

### Stage 1 — 选题

**用途**: 对每个候选题目搜现有解法、数据可得性、难度评估。

对每个候选题目:
```
semantic_search: "<题A核心问题> solution approach"
semantic_search: "<题B核心问题> benchmark dataset"
search_papers: 搜该领域近年论文数量趋势 (判断热度)
```

输出: 每个候选题目附 3-5 篇相关文献摘要，辅助选题决策。

### Stage 3 — 模型选型

**用途**: 搜每个候选模型的竞赛/学术应用案例，验证可行性。

```
semantic_search: "<模型名> application <问题类型>"
semantic_search: "<模型名> vs <替代模型> comparison"
semantic_search: "<模型名> implementation Python"
```

输出: 每个候选模型附 2-3 篇应用文献，填入选型决策矩阵的"文献支持"维度。

### Stage 5 — 子问题求解

**用途**: 文献 Agent 并行检索各 Qi 相关文献，搜特定技术细节、参数设置、算法改进。

```
semantic_search: "<方法> hyperparameter tuning"
semantic_search: "<方法> convergence analysis"
semantic_search: "<方法> improved version 改进"
content: 对关键方法的原文细节进行核验
```

输出: 每个子问题的求解策略有文献支撑。

### Stage 6 — 灵敏度分析

```
semantic_search: "sensitivity analysis <模型类型> Sobol Morris LHS"
```

### Stage 8 — 参考文献 (最重要)

**用途**: 文献 Agent 核验所有引用 + 补充检索 ≥10 条真实参考文献 (GB/T 7714 格式)。

```
search_papers: 按关键词 + 年份 + 期刊筛选
  → 返回完整元数据 (作者/标题/期刊/卷期/页码)
  → 自动格式化为 GB/T 7714
```

**关键**: 所有引用必须是真实文献 (Sciverse `doc_id` 可溯源)，**禁止虚构**。

---

## 检索策略

### 中文题目检索技巧

国赛题目虽为中文，但学术文献以英文为主:

```
# 中英混合检索
semantic_search: "无人机 烟幕干扰 UAV smoke interference optimization"

# 纯英文 (更全)
semantic_search: "crop planting optimization robust multi-objective"

# 找中文文献 (知网等)
semantic_search: "农作物种植 多目标优化 鲁棒"
# 注意: Sciverse 以英文文献为主, 中文覆盖较少
```

### Top-K 建议

| 场景 | top_k | 说明 |
|--------|-------|------------------|
| 快速了解 | 5-10 | Stage 0 背景预扫 |
| 标准调研 | 20-30 | Stage 1/3 选题选型 |
| 深度文献 | 50+ | Stage 8 文献综述 |

### 去重与质量控制

1. 同一主题多轮检索 → 按 doc_id 去重 (记录到 decision_log.sciverse_queries)
2. 优先 OA (开放获取) 论文 (content API 可读全文)
3. 优先高引论文 (search_papers 按 citations 排序)
4. 核验: 关键证据调 content API 读原文确认
5. 文献 Agent 在 Stage 8 对所有引用执行核验

---

## 限制与注意事项

| 项目 | 限制 |
|----------|----------------------------------------|
| 速率限制 | 60 请求 / 60 秒 (全 API 共享) |
| Token 获取 | https://sciverse.space/tokens (免费注册) |
| 文献覆盖 | 以英文为主，中文文献较少 |
| OA 全文 | 2,800 万篇 (仅 OA 论文可读全文) |
| 离线不可用 | 竞赛时需网络连接 |

**速率限制应对**:
- 不要对同一 query 反复调用 (结果缓存到 decision_log)
- 批量检索优于逐个检索
- 优先 semantic_search (一次获取多个相关结果)
- 多 Agent 并行时，文献 Agent 独占 Sciverse 调用，避免竞争

---

## 赛前检查清单

- [ ] `SCIVERSE_API_TOKEN` 环境变量已设置
- [ ] `claude mcp list` 确认 sciverse MCP 已安装
- [ ] 测试: 在 Claude Code 中说 "用 Sciverse 搜一篇关于 NSGA-II 的论文" 确认可用
- [ ] 速率限制: 60 req/min，多 Agent 并行时注意排队
