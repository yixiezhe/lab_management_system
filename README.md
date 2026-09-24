# 实验室管理系统 · LabOps Agent

面向实验室日常协作的全栈管理系统：采购与报销、仪器预约、项目与小组事务、
远程主机接入，以及可选的实验室运营智能助手。

> 当前为**私有开源候选版本**。分支已建立独立历史，主项目许可证与发布权利待确认。
> 不要直接将仓库设为公开。详见 [发布检查清单](docs/OPEN_SOURCE_READINESS.md)。

## 功能范围

- 用户、角色、导师/学生关系与业务数据访问控制。
- 公共采购、公对公采购、审批、发票、验收、付款与报销流程。
- 普通仪器、XRD、球磨机排队、多通道电化学工作站预约。
- 项目、公告、小组事务/采购和走廊展示配置。
- Guacamole 远程主机集成源码；端侧增强与实际连接配置不随发布提供。
- LabOps Agent：管理员侧边助手、受控业务查询、预约/采购表单预填，
  最终提交仍由用户点击原业务页面完成。
- 可选 RAG：知识解析与切分、Ollama BGE-M3 Dense Embedding、
  Qdrant 向量检索、关键词检索/RRF 融合、权限过滤与来源引用。

RAG 不是训练大模型。模型 API、文档知识索引和业务数据库是不同层；
身份、白名单、实时预约冲突等事实仍由后端业务规则校验。
当前代码不是任意 SQL Agent，也不是不受限制的自动执行器。

## 代码结构

| 目录 | 内容 |
| --- | --- |
| DjangoProject/ | Django、DRF、JWT、MySQL ORM 与迁移 |
| DjangoProject/labops_agent/ | LangGraph、LLM 接入、业务 Tools、RAG、评测与测试 |
| frontend/ | Vue 3、Vite、管理页面与助手组件 |
| database/demo_seed.json | 手工编写的虚构演示配置 |
| deploy/guacamole/ | 可选远程桌面接入说明 |
| scripts/ | 原有开发启停/备份工具，使用前审查环境参数 |
| docs/ | 架构、RAG、发布边界文档 |

不包含生产数据库、附件、导出账表、照片、凭据、模型权重、
node_modules、Python/Conda 环境或 Docker 镜像本体。

## 本机演示部署

以下命令只适用于你另外创建的**全新演示副本**，不要在现有生产/开发目录执行。
需要 Docker Compose；镜像版本继承已有项目配置，公开部署前必须进行版本和安全审查。
默认只有 MySQL、Django 后端、Nginx 前端，不要求 GPU、模型 API 或 Guacamole。

1. 克隆候选 main 到新目录，复制环境模板：

```powershell
git clone --branch main git@github.com:yixiezhe/lab_management_system.git lab-management-demo
Set-Location lab-management-demo
Copy-Item .env.example .env
```

2. 自行生成密钥并填入 .env。以下命令需要 Python 3，只生成新值：

```sh
python -c "import base64,secrets; print('DJANGO_SECRET_KEY='+secrets.token_urlsafe(48)); print('FERNET_KEY='+base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()); print('MYSQL_ROOT_PASSWORD='+secrets.token_urlsafe(24))"
```

不要把输出提交到 Git 或贴到公共讨论区。
MYSQL_PASSWORD 与 MYSQL_ROOT_PASSWORD 保持一致（此演示使用 root，生产应使用最小权限账号）。
保持 Agent/RAG 开关关闭，先验证基础系统。

3. 启动全新演示环境：

```sh
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 backend
```

后端启动时对新库执行 migrate。等迁移完成后再进行下一步。
端口只绑定 127.0.0.1：前端 5173，后端 8000，MySQL 3307。
这是 Django runserver 开发配置，不是可直接对公网开放的生产方案。

4. 导入虚构配置并交互式设置管理员密码（PowerShell）：

```powershell
docker compose run --rm --no-deps -v "${PWD}/database:/demo:ro" backend python manage.py seed_local_labops --fixture /demo/demo_seed.json
```

账号为 localadmin，密码由你输入，至少 12 个字符，无内置默认密码。
此命令会更新同名演示配置和管理员，**仅对新的演示数据库执行**。
示例包含两台虚构仪器、一个平台及一条白名单；不会创建真实采购或预约流水。

打开 [本机前端](http://127.0.0.1:5173)，用上述账号登录。
仪器照片不包含在快照中，页面使用默认占位展示。

## 可选功能

- [启用模型 API 与 RAG](docs/RAG_本地部署与体验指南.md)
- [Guacamole 接入与未包含的增强功能](deploy/guacamole/README.md)

Agent/RAG 默认关闭；启用时自行配置提供商、模型名、API Key。
本仓库不提供任何共享令牌。调用模型可能产生费用，也可能向模型服务商传递
经权限过滤的业务信息，上线前需评估数据处理范围。

## 验证与生产注意事项

建议在新的隔离演示环境执行：

```sh
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py test labops_agent.tests
docker compose build frontend
```

本仓库提供 GitHub Actions 隔离验收，实际通过情况以对应提交的运行结果为准。
测试范围与限制见 [验证记录](docs/PREPARATION_VALIDATION.md)。
正式部署还需要 HTTPS、正式应用服务器、最小权限数据库账号、备份恢复、
依赖漏洞排查、私有媒体访问控制和完整权限回归。
Docker 数据卷保存数据库与上传文件；不要无意删除数据卷。

## 进一步阅读

- [后端代码职责](docs/architecture/backend.md)
- [前端与业务流程](docs/architecture/frontend-and-flows.md)
- [采购流程](Procurement_process_readme.md)
- [远程连接源码说明](远程连接readme.md)
- [RAG 设计与阶段计划](docs/LabOps_Agent_RAG_详细设计与实施方案.md)
- [开源准备检查清单](docs/OPEN_SOURCE_READINESS.md)
- [第三方组件与许可边界](THIRD_PARTY_NOTICES.md)

架构导读保留自原维护文档，个别历史描述需以当前代码为准；
RAG 设计文档中的规划不等于全部已经实现。
