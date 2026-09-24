# 后端代码职责索引

从原维护文档保留的源码导读，实际行为以当前代码为准。

## 4. 后端目录与代码职责

### 4.1 `DjangoProject/` 顶层结构

| 路径 | 作用 |
| --- | --- |
| `DjangoProject/manage.py` | Django 命令入口，用于启动服务、迁移、建超级管理员等。 |
| `DjangoProject/DjangoProject/__init__.py` | Django 项目包标识文件。 |
| `DjangoProject/DjangoProject/settings.py` | 全局配置中心，包含数据库、已安装 app、JWT、CORS、媒体目录、自定义用户模型等配置。 |
| `DjangoProject/DjangoProject/urls.py` | 全局路由汇总，把各 app 统一挂载到 `/api/*`。 |
| `DjangoProject/DjangoProject/asgi.py` | ASGI 入口。 |
| `DjangoProject/DjangoProject/wsgi.py` | WSGI 入口。 |
| `DjangoProject/templates/` | Django 顶层模板目录，当前基本为空，属于保留目录。 |
| `DjangoProject/media/` | 用户上传文件目录，按业务类型分子目录存储附件。 |
| `DjangoProject/.idea/` | 后端子工程的 JetBrains 配置，不参与部署。 |

### 4.2 Django app 内常见文件的统一含义

仓库中多数后端 app 结构相似，常见文件职责如下：

| 文件/目录 | 作用 |
| --- | --- |
| `__init__.py` | Python 包标识。 |
| `apps.py` | Django app 注册配置。 |
| `admin.py` | Django Admin 注册、后台管理扩展。 |
| `models.py` | 数据表模型定义，是数据库结构与业务字段的主来源。 |
| `serializers.py` | DRF 序列化器，负责接口入参与出参转换。 |
| `views.py` 或 `views/` | 业务接口实现。 |
| `urls.py` | 当前 app 的接口路由。 |
| `permissions.py` | 自定义权限控制。 |
| `filters.py` | 列表页与台账页的筛选逻辑。 |
| `signals.py` | 模型信号联动逻辑。 |
| `migrations/` | 数据库迁移历史。 |
| `tests.py` | 自动化测试入口；当前大多仍是模板占位。 |
| `__pycache__/` | Python 缓存文件，可忽略。 |

### 4.3 核心 app 逐个说明

#### 4.3.1 `users/`

用户与角色中心，是系统权限控制的基础。

- `models.py`
  - 定义自定义用户 `UserProfile`
  - 定义角色 `Role`
  - 定义密码重置申请 `PasswordResetRequest`
  - 支持导师-学生、自关联导师分配、系统管理员/走廊屏管理员/land 主机账号等角色衍生能力
- `serializers.py`
  - 用户注册、用户详情、导师列表、角色分配、密码重置等序列化逻辑
- `views.py`
  - 提供注册、当前用户信息、导师列表、成员管理、密码重置申请、角色分配等接口
- `urls.py`
  - 暴露 `/api/users/` 下相关接口
- `admin.py`
  - 管理员后台注册用户与角色模型
- `tests.py`
  - 当前主要是占位

#### 4.3.2 `procurement/`

采购主业务 app，是整个系统最核心的后端模块。

- `models.py`
  - `PurchaseRequest`：采购主单
  - `RequestItem`：采购明细
  - `Platform`：采购平台
  - `WhitelistItem`：白名单条目
  - `GlobalAnnouncement`：全局公告
  - 支持父子申请合并、流程状态、经费类型、公对公标记等关键字段
- `serializers.py`
  - 采购申请创建/编辑/列表/详情序列化
  - 平台、白名单、公告、台账等输出结构
- `filters.py`
  - 采购台账筛选器
  - 把前端的“待报销”语义映射为 `accepted + inspection_skipped`
- `permissions.py`
  - 采购审批、管理员、处理人等权限控制
- `signals.py`
  - 采购流程联动信号入口
- `urls.py`
  - 汇总采购主路由
- `_views_backup.py`
  - 历史备份代码，不是当前主路由入口

`procurement/views/` 下是实际使用的视图拆分目录：

- `views/admin.py`
  - 采购后台管理相关的扩展逻辑
- `views/main/purchase_request_views.py`
  - 公共经费与公对公采购申请的创建、查询、审批、驳回、撤回、提交链接等主流程接口
- `views/main/ledger_views.py`
  - 全流程台账、详情、合并父子单台账输出
- `views/main/utility_views.py`
  - 合并/撤销合并、附件打包、报销图片打包、批量删除、统计、平台管理、白名单、公告等工具接口

`procurement/templates/` 下有两个自定义后台模板：

- `templates/admin/excel_import.html`
  - 后台 Excel 导入界面模板
- `templates/admin/whitelist_changelist.html`
  - 白名单后台管理界面模板

#### 4.3.3 `common_serializers/`

采购全流程的公共序列化中心，用来把多个 app 的一对一/一对多数据整合成统一输出。

- `serializers.py`
  - 把采购主单、明细、付款、发票、验收、报销、请购单、合同等数据整合成“全流程详情”
  - 同时兼容 `invoice`（最新发票）与 `invoices`（全部发票列表）
  - 支持展开合并父单与子单信息
- `models.py` / `views.py` / `admin.py` / `tests.py`
  - 基本为 Django app 占位结构，业务重心在 `serializers.py`

#### 4.3.4 `invoice/`

发票模块。

- `models.py`
  - 定义 `Invoice`
  - 与采购主单是一对多关系，当前代码已支持一张申请对应多张发票
- `serializers.py`
  - 发票上传、查询、更新的序列化
- `views.py`
  - 发票列表、上传、编辑等接口
- `urls.py`
  - 暴露 `/api/invoice/` 路由
- 业务特点
  - 支持 TIFF 转 PNG 处理
  - 通过模型联动推动采购状态从收货进入开票/免验收后的下一阶段

#### 4.3.5 `payment/`

付款模块。

- `models.py`
  - 定义 `Payment`，存储付款截图/凭证
- `serializers.py`
  - 付款记录的输入输出
- `views.py`
  - 付款创建、查询、驳回等接口
- `urls.py`
  - 暴露 `/api/payment/` 路由
- 业务特点
  - 公共经费审批通过时会直接生成付款记录
  - 提供付款驳回接口，状态会转到 `payment_rejected`

#### 4.3.6 `acceptance/`

收货确认模块。

- `models.py`
  - 定义 `Acceptance`
- `serializers.py`
  - 收货确认序列化
- `views.py`
  - 申请人确认收货接口
- `permissions.py`
  - 只允许符合条件的用户操作
- `urls.py`
  - 暴露 `/api/acceptance/` 路由
- 业务特点
  - 收货后状态从 `paid` 推进到 `goods_received`

#### 4.3.7 `inspection/`

验收模块。

- `models.py`
  - 定义 `Inspection`
- `serializers.py`
  - 验收记录序列化
- `views.py`
  - 验收创建与查询接口
- `urls.py`
  - 暴露 `/api/inspection/` 路由
- 业务特点
  - 发票到位且需要验收时，由该模块把状态从 `invoiced` 推进到 `accepted`

#### 4.3.8 `expense_report/`

报销凭证模块之一，偏历史兼容路径。

- `models.py`
  - 定义 `ExpenseReport`
- `serializers.py`
  - 报销附件、金额、备注等序列化
- `views.py`
  - 报销凭证提交与查询接口
- `urls.py`
  - 暴露 `/api/expense-reports/` 路由
- 业务特点
  - 提交后可把已验收或免验收申请推进到 `reimbursed`

#### 4.3.9 `reimbursement/`

报销模块之二，是当前代码中更完整的报销实现。

- `models.py`
  - 定义 `Reimbursement`
- `serializers.py`
  - 支持实际报销金额、附件集合等字段
- `views.py`
  - 报销提交、查询、编辑等接口
- `urls.py`
  - 暴露 `/api/reimbursement/` 路由
- 业务特点
  - 兼容合并父子单报销
  - 子单维持 `merged` 状态，全部子单报销后父单再进入 `reimbursed`

#### 4.3.10 `purchase_order/`

公对公请购单模块。

- `models.py`
  - 定义 `PurchaseOrder`
- `serializers.py`
  - 将后端字段映射成前端使用的 `order_file` 等命名
- `views.py`
  - 请购单上传、查看、更新接口
- `urls.py`
  - 暴露 `/api/purchase-orders/` 路由
- 业务特点
  - 提交后一般会把公对公流程从 `pending_purchase_order` 推进到 `pending_contract`

#### 4.3.11 `contract/`

公对公合同模块。

- `models.py`
  - 定义 `Contract`
- `serializers.py`
  - 将后端字段映射成前端使用的 `contract_file`
- `views.py`
  - 合同上传、查看、更新接口
- `urls.py`
  - 暴露 `/api/contracts/` 路由
- 业务特点
  - 提交后一般把流程从 `pending_contract` 推进到 `paid`

#### 4.3.12 `team_procurement/`

小组采购模块，与主采购流程平行存在。

- `models.py`
  - `TeamPurchaseRequest`
  - `TeamRequestItem`
  - 状态枚举当前只有 `pending / approved / rejected / completed / withdrawn`
- `serializers.py`
  - 小组申请及明细序列化
- `views.py`
  - 小组采购申请、审批、撤回、台账接口
- `filters.py`
  - 小组台账筛选逻辑
- `permissions.py`
  - 小组管理员与成员权限
- `urls.py`
  - 暴露 `/api/team-procurement/` 路由

#### 4.3.13 `projects/`

项目管理模块。

- `models.py`
  - 定义实验室项目实体
- `serializers.py`
  - 项目详情与列表输出
- `views.py`
  - 项目 CRUD、发布到首页、公开列表
- `urls.py`
  - 暴露 `/api/projects/` 路由
- 业务特点
  - 公开项目列表会写入 Django 缓存，首页通过发布列表接口读取

#### 4.3.14 `equipment/`

仪器管理与预约模块。

- `models.py`
  - `Equipment`
  - `Booking`
  - 仪器可预约规则、提前预约天数、早鸟用户策略
- `serializers.py`
  - 仪器详情、预约记录、可用时段序列化
- `views.py`
  - 仪器 CRUD、可预约时段、预约创建/取消、我的预约、历史预约
- `permissions.py`
  - 仪器管理权限控制
- `urls.py`
  - 暴露 `/api/equipment/` 路由

#### 4.3.15 `remote_access/`

远程主机预约与会话管理模块。

- `models.py`
  - `RdpMachine`
  - `RdpBooking`
  - 机器状态、设备密钥、密码加密、占用关系等
- `serializers.py`
  - 主机与预约数据序列化
- `views.py`
  - 主机管理、预约、连接、断开、状态心跳、插队申请与审批、设备登录
- `permissions.py`
  - 管理员、设备端、普通用户的权限区分
- `urls.py`
  - 暴露 `/api/remote_access/` 路由
- 业务特点
  - `device_login` 支持走廊设备/落地主机类终端自动登录
  - 机器密码采用加密与密钥校验方案存储

#### 4.3.16 `corridor_display/`

走廊显示屏模块。

- `models.py`
  - `DisplayImage`
  - `DisplayConfig`
- `serializers.py`
  - 图片、排序、配置输出
- `views.py`
  - 图片上传、删除、排序、配置更新、公开展示数据
- `urls.py`
  - 暴露 `/api/corridor_display/` 路由
- 业务特点
  - `/api/corridor_display/public/` 是公开接口，前端展示页据此获取图片与配置

### 4.4 `media/` 上传目录说明

`DjangoProject/media/` 是运行时附件目录，不是源码，但对业务很重要。

| 子目录 | 用途 |
| --- | --- |
| `media/acceptances/` | 收货确认附件，按年份分目录。 |
| `media/contracts/` | 合同附件，按年份分目录。 |
| `media/corridor_display/images/` | 走廊显示屏图片资源。 |
| `media/inspections/` | 验收附件，按年份分目录。 |
| `media/invoices/` | 发票图片/文件，按年份分目录。 |
| `media/payments/` | 付款截图/凭证，按年份分目录。 |
| `media/purchase_orders/` | 公对公请购单文件。 |
| `media/reimbursements/` | 报销附件，既有按年份目录，也有按报销记录 ID 分目录的历史结构。 |
