# 智能旅游 AI 管家

基于 LangChain + LangGraph + Streamlit 构建的一站式智能旅游规划系统，集成 RAG 检索增强生成、多智能体工作流、用户画像管理等核心技术。

## 项目架构

```
├── app.py                    # Streamlit 主入口（用户认证 + 对话界面）
├── agent/                    # 智能体核心模块
│   ├── react_agent.py        # LangGraph 多智能体工作流引擎
│   ├── state.py              # 全局状态定义（TypedDict）
│   ├── skills/               # 技能插件系统
│   │   ├── context/          # 环境感知技能（时间、定位）
│   │   ├── external/         # 外部交互技能（天气、导航、小红书）
│   │   └── profile/          # 用户画像技能（RAG、画像管理）
│   ├── tools/                # 工具定义（旧版，已被 skills 替代）
│   └── rag/                  # 三表隔离向量库架构
│       ├── base_chroma.py    # Chroma 向量库基类
│       ├── history_record.py # 历史记录向量库
│       ├── user_profile.py   # 用户画像向量库
│       └── public_knowledge.py # 公共知识向量库
├── rag/                      # RAG 检索服务
│   ├── rag_service.py        # RAG 总结服务（HyDE + 阈值熔断）
│   └── vector_store.py       # 向量库服务（文档加载、切分、检索）
├── model/                    # 模型工厂
│   └── factory.py            # 通义千问聊天/嵌入模型工厂
├── config/                   # 配置文件
│   ├── agent.yml             # Agent 配置（API Key、外部数据路径）
│   ├── chroma.yml            # Chroma 向量库配置（三表隔离）
│   ├── rag.yml               # RAG 模型配置
│   └── prompts.yml           # 提示词路径配置
├── prompts/                  # 提示词模板
│   ├── main_prompt.txt       # 主系统提示词（四阶段 SOP）
│   ├── phase1_explore.txt    # 阶段一：需求探索
│   ├── phase2_plan.txt       # 阶段二：路书规划
│   ├── phase3_feedback.txt   # 阶段三：反馈收集
│   ├── report_prompt.txt     # 阶段四：旅行报告
│   └── rag_summarize.txt     # RAG 总结提示词
├── utils/                    # 工具函数
│   ├── config_handler.py     # YAML 配置加载器
│   ├── gateway_handler.py    # 意图识别网关（Query 改写）
│   ├── file_handler.py       # 文件加载工具（PDF/TXT）
│   ├── logger_handler.py     # 日志工具
│   ├── path_tool.py          # 路径工具
│   └── prompt_loader.py      # 提示词加载器
├── data/                     # 知识库源文件
├── logs/                     # 日志文件
├── chroma_db/                # Chroma 向量数据库持久化目录
├── requirements.txt          # Python 依赖
└── Dockerfile                # Docker 容器化配置
```

---

## 核心模块详解

### 1. Streamlit 前端入口 (`app.py`)

**功能**：提供 Web 界面，包含用户认证和对话交互。

**技术方案**：
- **Streamlit**：Python Web 框架，快速构建交互式界面
- **用户认证**：基于 JSON 文件的轻量级用户数据库，支持登录/注册
- **会话管理**：使用 `st.session_state` 维护用户状态和对话历史
- **流式输出**：通过生成器实现打字机效果，提升用户体验

**核心流程**：
```
用户输入 → 组装短期记忆 → 调用 ReactAgent.execute_stream() → 流式返回结果
```

---

### 2. 多智能体工作流引擎 (`agent/react_agent.py`)

**功能**：基于 LangGraph 构建的状态机，实现五节点协作的旅游规划流程。

**技术方案**：
- **LangGraph**：LangChain 的图计算框架，支持条件路由和循环
- **StateGraph**：全局状态字典在节点间传递数据
- **条件路由**：根据质检结果决定是否重新规划

**五节点架构**：

```
START → Gateway → Memory → Retriever → Creator → Evaluator → END
                ↓ (闲聊)
               END
```

| 节点 | 功能 | 核心技术 |
|------|------|----------|
| **Gateway** | 意图识别、Query 改写、数据回写 | Structured Output、CQRS 模式 |
| **Memory** | 结构化记忆（目的地、天数、预算等） | Pydantic Schema、JSON 红线 |
| **Retriever** | 四路并发策略检索 | 向量检索、MCP 协议 |
| **Creator** | 基于反馈的路书起草 | Prompt Engineering |
| **Evaluator** | 质检审计（红线违规、意图偏离、事实错误） | Structured Output、循环修订 |

**状态定义** (`agent/state.py`)：
```python
class TravelState(TypedDict):
    user_id: str
    query: str
    short_term_history: str
    is_chitchat: bool
    chitchat_reply: str
    true_intent: str
    rag_keyword: str
    mcp_keyword: str
    facts_context: str
    draft_itinerary: str
    revision_count: int
    eval_status: Literal["Pass", "Fail", "Pending"]
    feedback: str
    travel_spec: dict
```

---

### 3. 意图识别网关 (`utils/gateway_handler.py`)

**功能**：前置智能网关，负责意图识别、Query 改写和数据回流。

**技术方案**：
- **Structured Output**：使用 Pydantic Schema 约束 LLM 输出
- **指代消解**：结合历史对话推断代词指代
- **CQRS 数据回流**：实时提取用户画像和评价，写入向量库

**输出结构**：
```python
class GatewayOutput(BaseModel):
    is_chitchat: bool           # 是否闲聊
    chitchat_reply: str         # 闲聊回复
    true_intent: str            # 真实意图
    rag_keyword: str            # RAG 检索词
    mcp_keyword: str            # MCP 检索词
    has_profile_update: bool    # 是否更新画像
    extracted_profile: str      # 提取的画像
    is_review: bool             # 是否是评价
    review_target: str          # 评价目标
    review_rating: float        # 评分
    review_content: str         # 评价内容
```

---

### 4. RAG 检索增强生成 (`rag/`)

#### 4.1 向量库服务 (`rag/vector_store.py`)

**功能**：封装 Chroma 向量库的初始化、文档加载、切分、检索。

**技术方案**：
- **Chroma**：开源向量数据库，支持持久化
- **RecursiveCharacterTextSplitter**：递归文本分割器
- **MD5 去重**：增量更新，避免重复加载
- **kwargs 透传**：支持动态参数传递

**核心方法**：
| 方法 | 功能 |
|------|------|
| `get_retriever()` | 获取向量检索器，支持动态参数 |
| `upsert_text()` | 直接存入纯文本（供画像 Skill 调用） |
| `similarity_search()` | 语义检索相似向量 |
| `load_document()` | 从目录加载 TXT/PDF，MD5 去重后切分入库 |

#### 4.2 RAG 总结服务 (`rag/rag_service.py`)

**功能**：基于 HyDE 机制和阈值熔断的高质量检索服务。

**技术方案**：
- **HyDE (Hypothetical Document Embeddings)**：将短 Query 升维为长段假设性文档，扩充语义特征
- **阈值熔断**：相似度 < 0.8 直接丢弃，防止幻觉
- **Prompt Template**：将检索结果和用户问题喂给 LLM 做最终总结

**核心流程**：
```
用户 Query → HyDE 升维 → 向量检索 (阈值=0.8) → 上下文拼装 → LLM 总结
```

---

### 5. 三表隔离向量库架构 (`agent/rag/`)

**功能**：将不同类型的数据存储在独立的 Chroma Collection 中，实现物理隔离。

**技术方案**：
- **BaseChromaDB**：向量库基类，封装 Chroma 初始化
- **Collection 隔离**：不同业务使用不同的 Collection，避免数据污染
- **Metadata 过滤**：通过 metadata 实现精准查询

**三表架构**：

| 表名 | 用途 | Collection Name |
|------|------|-----------------|
| **公共知识库** | 攻略、景点大全、用户评价 | `public_knowledge` |
| **用户画像库** | 个人偏好、忌口、体力标签 | `travel_user_profiles` |
| **历史记录库** | 多轮对话上下文记忆 | `travel_history_records` |

**各表实现**：

- **PublicKnowledgeDB** (`public_knowledge.py`)：
  - `search_knowledge()`：公共知识检索
  - `add_review()`：新增用户评价（UGC）

- **UserProfileDB** (`user_profile.py`)：
  - `upsert_profile()`：插入/更新用户画像
  - `get_user_profiles()`：获取用户画像（Metadata 过滤）

- **HistoryRecordDB** (`history_record.py`)：
  - `add_log()`：追加聊天记录
  - `recall_history()`：召回历史原话（语义检索）

---

### 6. 技能插件系统 (`agent/skills/`)

**功能**：基于 Registry Pattern 的技能管理，支持热插拔。

**技术方案**：
- **SkillManager**：技能注册与管理器
- **BaseTool**：LangChain 工具基类，定义统一接口
- **Pydantic Schema**：约束输入参数

**技能清单**：

#### 环境感知技能 (`context/`)

| 技能 | 功能 | 技术方案 |
|------|------|----------|
| `TimePerceptionSkill` | 获取当前时间、日期、季节 | datetime 模块 |
| `LocationPerceptionSkill` | 获取用户真实位置 | 高德 IP 定位 + 逆地理编码 |

#### 外部交互技能 (`external/`)

| 技能 | 功能 | 技术方案 |
|------|------|----------|
| `WeatherQuerySkill` | 查询城市天气 | 高德天气 API |
| `TransitRouteSkill` | 公交/地铁换乘规划 | 高德公交路径规划 API |
| `XhsMcpSearchSkill` | 小红书笔记搜索 + 详情抓取 | MCP 协议、JSON-RPC |

#### 用户画像技能 (`profile/`)

| 技能 | 功能 | 技术方案 |
|------|------|----------|
| `UpdateUserProfileSkill` | 结构化保存用户画像 | 强类型 Schema、向量库 upsert |
| `GetUserProfileSkill` | 读取用户画像 | Metadata 精确过滤 |
| `FindSimilarVibeSkill` | 寻找相似偏好用户 | 语义相似度检索 |
| `RagSkill` | 内部知识库 RAG 检索 | HyDE + 阈值熔断 |
| `SaveGlobalFeedbackSkill` | 存储用户评价到公共库 | 向量库 upsert |

---

### 7. 模型工厂 (`model/factory.py`)

**功能**：基于抽象工厂模式生成通义千问模型实例。

**技术方案**：
- **抽象工厂模式**：BaseModelFactory 定义接口，ChatModelFactory 和 EmbeddingsFactory 分别实现
- **通义千问**：阿里云大模型，支持聊天和嵌入

**模型配置**：
```yaml
# config/rag.yml
chat_model_name: qwen3-max
embedding_model_name: text-embedding-v4
```

---

### 8. 配置管理 (`config/`)

**功能**：YAML 配置文件统一管理。

**配置文件**：

| 文件 | 用途 |
|------|------|
| `agent.yml` | API Key、外部数据路径 |
| `chroma.yml` | 三表隔离配置、文本切分参数 |
| `rag.yml` | 聊天/嵌入模型名称 |
| `prompts.yml` | 提示词文件路径 |

---

### 9. 提示词工程 (`prompts/`)

**功能**：四阶段 SOP 提示词体系。

**四阶段流程**：

| 阶段 | 文件 | 功能 |
|------|------|------|
| 阶段一 | `phase1_explore.txt` | 需求探索与三维交叉验证 |
| 阶段二 | `phase2_plan.txt` | 保姆级路书生成 |
| 阶段三 | `phase3_feedback.txt` | 行程结束后的反馈收集 |
| 阶段四 | `report_prompt.txt` | 旅行总结与足迹报告 |

**RAG 提示词** (`rag_summarize.txt`)：
- 约束 LLM 基于参考资料回答，禁止编造
- 要求中文、客观、简洁

---

### 10. 工具函数 (`utils/`)

| 模块 | 功能 |
|------|------|
| `config_handler.py` | YAML 配置加载器，全局配置实例化 |
| `gateway_handler.py` | 意图识别网关（详见第 3 节） |
| `file_handler.py` | PDF/TXT 文件加载、MD5 计算 |
| `logger_handler.py` | 日志工具（控制台 + 文件双输出） |
| `path_tool.py` | 绝对路径工具 |
| `prompt_loader.py` | 提示词加载器（四阶段拼接） |

---

## 技术栈

| 类别 | 技术 |
|------|------|
| **前端框架** | Streamlit |
| **Agent 框架** | LangChain + LangGraph |
| **向量数据库** | Chroma |
| **大模型** | 通义千问 (qwen3-max) |
| **嵌入模型** | text-embedding-v4 |
| **外部 API** | 高德地图（天气、定位、导航）、小红书 MCP |
| **数据验证** | Pydantic |
| **配置管理** | PyYAML |
| **容器化** | Docker |

---

## 核心设计亮点

### 1. 五节点状态机工作流
基于 LangGraph 的条件路由，实现"网关→记忆→检索→起草→质检"的完整闭环，支持循环修订（最多 3 次）。

### 2. 三表隔离向量库架构
公共知识、用户画像、历史记录物理隔离，避免数据污染，支持 Metadata 精确过滤。

### 3. HyDE + 阈值熔断
将短 Query 升维为假设性文档，扩充语义特征；相似度 < 0.8 直接丢弃，防止幻觉。

### 4. CQRS 数据回流
Gateway 实时提取用户画像和评价，写入向量库，实现"对话即数据采集"。

### 5. 四阶段 SOP 提示词体系
从需求探索到反馈收集，每个阶段有独立的提示词，LLM 自主判断当前阶段。

### 6. 技能热插拔
基于 Registry Pattern 的技能管理器，新增技能只需一行注册代码。

---

## 快速启动

### 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
streamlit run app.py
```

### Docker 运行

```bash
# 1. 构建镜像
docker build -t travel-agent .

# 2. 运行容器
docker run -p 8501:8501 travel-agent
```

访问 http://localhost:8501 即可使用。

---

## 配置说明

### API Key 配置

在 `config/agent.yml` 中配置：

```yaml
HEWEATHER_KEY: your_heweather_key
AMAP_KEY: your_amap_key
```

### Chroma 向量库配置

在 `config/chroma.yml` 中配置：

```yaml
# 三表隔离
collection_name: public_knowledge
profile_collection_name: travel_user_profiles
history_collection_name: travel_history_records

# 文本切分
chunk_size: 200
chunk_overlap: 20
```

---

## 项目特色

1. **一站式服务**：用户无需打开其他 APP，即可完成天气查询、路线规划、攻略检索、避坑指南
2. **个性化推荐**：基于用户画像和历史记录，提供定制化旅游方案
3. **实时排雷**：集成小红书 MCP，获取最新避坑信息
4. **系统进化**：用户反馈自动存入知识库，影响未来推荐策略
5. **保姆级路书**：包含时间节点、精准交通、酒店餐饮、避坑贴士的完整执行方案
