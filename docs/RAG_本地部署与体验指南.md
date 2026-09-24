# LabOps Agent / RAG 演示指南

适用于按根目录 README 部署的全新演示副本。
不依赖原实验室数据库，不默认提供任何管理员密码、模型 Key 或预建知识索引。
不要在现有生产/开发环境中照搬这些命令。

## 1. 先启用模型 API

在 .env 中填写：

```dotenv
LABOPS_AGENT_ENABLED=True
LABOPS_AGENT_USE_LANGGRAPH=True
LABOPS_LLM_BASE_URL=https://model.example.invalid/v1
LABOPS_LLM_API_KEY=
LABOPS_LLM_MODEL=
```

示例域名不可用，必须替换为你有权使用的兼容接口；模型需要支持本项目使用的工具调用协议。
自行填写有效 Key 与实际模型名，不要提交到 Git。是否兼容需要对所选服务实测。

```sh
docker compose up -d backend
```

使用自己设置的管理员账号登录前端，打开侧边助手。
先体验“有哪些仪器可以预约”“我的采购申请有哪些”。
演示库没有采购流水，空结果是正常情况。
非管理员仍应被后端拒绝；模型不能绕过业务权限或直接提交订单/预约。

## 2. 启动可选知识索引服务

默认 CPU 路线：

```sh
docker compose --profile rag up -d
docker compose logs --tail 100 ollama-model-loader
```

这会启动 Qdrant、Ollama，并下载配置的 BGE-M3 模型。
等待模型下载完成；CPU 性能取决于机器配置，不保证实时响应速度。
可用以下命令查看已加载模型：

```sh
docker compose exec ollama ollama list
```

若有已配置好的 GPU 容器运行环境，使用可选覆盖文件：

```sh
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile rag up -d
```

后续 Compose 操作应保持使用相同的文件组合。
本准备分支未对你的演示硬件运行 GPU 验收，不声称任何显卡配置均兼容。

## 3. 启用 RAG

把 .env 中 LABOPS_RAG_ENABLED 改为 True，再重建该副本的后端容器：

```sh
docker compose --profile rag up -d backend
docker compose exec backend python manage.py check_labops_index --probe-embedding
```

默认服务配置：Qdrant http://qdrant:6333、Ollama http://ollama:11434、
模型 bge-m3、向量维度 1024。
不要在已有集合中随意更换不同维度的 Embedding 模型。
主机端口只绑定本机，远程部署需要自行配置鉴权和网络隔离。

## 4. 导入知识

目前支持 UTF-8 Markdown、TXT 和 HTML，不是完整 PDF/OCR 管道。
先审查文档授权、准确性与隐私；不要导入密码、真实账单、私人审批备注或聊天指令。
例如在 PowerShell 中导入仓库自带流程文档，先只解析不写入：

```powershell
docker compose run --rm --no-deps -v "${PWD}/Procurement_process_readme.md:/knowledge/procurement.md:ro" backend python manage.py ingest_labops_knowledge --path /knowledge/procurement.md --title 演示采购流程 --domain procurement --document-version demo-v1 --visibility admin --dry-run
```

确认解析结果后去掉 --dry-run 才会写入 MySQL 与 Qdrant。
文档中流程是本项目规则说明，不等于你所在机构现行制度。
不要把个人业务数据作为公开知识文档导入。

## 5. 实际链路与边界

- Markdown/TXT/HTML 解析、章节切分与知识元数据入库。
- BGE-M3 Dense Embedding + Qdrant 向量检索。
- MySQL Chunk 关键词召回与 RRF 融合；不是已经实现 BM25 或 BGE Reranker。
- 权限、发布状态与有效期过滤，向模型传入有上限的引用片段。
- LangGraph 中结合业务 Tools，输出回答与来源。
- 白名单平台、经费类别、实时预约空闲和冲突以业务数据库及原规则为准。
- 采购/预约仅预填，最后提交由用户点击，仍走原 API 校验。

可以尝试：

- “公共采购需要经过哪些步骤？”
- “帮我预约演示普通仪器，明天上午 8 点开始，2 小时。”
- “帮我买 2 个演示玻璃样品瓶。”

具体能否预填取决于信息完整性、设备规则、可用时段和模型服务兼容性。
没有可靠依据时应明确说明，不能编造来源或虚构已完成操作。

## 6. 验收与故障定位

```sh
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test labops_agent.tests
docker compose exec backend python manage.py check_labops_index --probe-embedding
docker compose logs --tail 100 backend qdrant ollama
```

检查管理员权限、引用可访问性、越权请求、无结果/超时降级、
问答是否意外创建业务记录，以及最后提交是否仍由用户主动确认。
上述是待运行的验收步骤，不是本次整理已完成的性能或效果测量。

关闭 LABOPS_RAG_ENABLED 并重建演示后端可只保留普通助手。
关闭 LABOPS_AGENT_ENABLED 可禁用模型功能；原采购和仪器页面仍独立存在。
