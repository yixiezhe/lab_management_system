# 前端与业务流程索引

从原维护文档保留的源码导读。数据库备份不随发布提供；部署以根目录 README 为准。

## 5. 前端目录与代码职责

### 5.1 `frontend/` 顶层结构

| 路径 | 作用 |
| --- | --- |
| `frontend/package.json` | 前端依赖与脚本定义。 |
| `frontend/package-lock.json` | npm 锁文件。 |
| `frontend/vite.config.js` | Vite 构建配置。 |
| `frontend/index.html` | Vite 入口 HTML。 |
| `frontend/eslint.config.js` | ESLint 配置。 |
| `frontend/jsconfig.json` | JS 工程配置。 |
| `frontend/.editorconfig` | 编辑器格式约束。 |
| `frontend/.gitattributes` | Git 属性配置。 |
| `frontend/.gitignore` | Git 忽略规则。 |
| `frontend/.prettierrc.json` | Prettier 格式化配置。 |
| `frontend/.vscode/` | VS Code 推荐扩展与工作区设置。 |
| `frontend/public/` | 打包时直接拷贝的静态资源。 |
| `frontend/src/` | 前端业务源码主目录。 |
| `frontend/dist/` | 已构建产物目录，不是业务源码。 |
| `frontend/node_modules/` | 第三方依赖目录。 |
| `frontend/README.md` | Vite 模板自带 README，不是项目主文档。 |

### 5.2 `frontend/public/`

| 路径 | 作用 |
| --- | --- |
| `frontend/public/logo.svg` | 站点图标。 |
| `frontend/public/logo.svg` | 站点 logo。 |

### 5.3 `frontend/src/` 总体分层

| 目录/文件 | 作用 |
| --- | --- |
| `src/main.js` | Vue 应用入口，挂载路由、Pinia、Element Plus。 |
| `src/App.vue` | 全局应用壳层。 |
| `src/api/` | Axios 封装与业务 API 调用。 |
| `src/router/` | 路由定义与权限守卫。 |
| `src/stores/` | Pinia 状态管理。 |
| `src/assets/` | 全局样式与静态资源。 |
| `src/components/` | 可复用业务组件。 |
| `src/views/` | 页面级视图组件。 |

### 5.4 `src/api/`

| 文件 | 作用 |
| --- | --- |
| `src/api/index.js` | Axios 主实例，负责 JWT 注入、401 刷新令牌、设备端登录兼容、通用错误处理。 |
| `src/api/equipment.js` | 仪器预约相关接口封装。 |
| `src/api/remote_access.js` | 远程访问相关接口封装。 |

### 5.5 `src/router/`

| 文件 | 作用 |
| --- | --- |
| `src/router/index.js` | 全站路由配置、登录守卫、角色守卫、land 主机账号的访问限制。 |

### 5.6 `src/stores/`

| 文件 | 作用 |
| --- | --- |
| `src/stores/auth.js` | 当前用户、角色权限、首页角标统计、登录态管理。 |
| `src/stores/counter.js` | Vue 模板残留文件，非业务核心。 |

### 5.7 `src/assets/`

| 文件 | 作用 |
| --- | --- |
| `src/assets/base.css` | 基础样式。 |
| `src/assets/main.css` | 主样式入口。 |
| `src/assets/logo.svg` | 模板 logo，业务价值较低。 |

### 5.8 `src/components/` 组件说明

#### 采购与报销相关组件

| 文件 | 作用 |
| --- | --- |
| `src/components/ProcurementForm.vue` | 采购申请表单主组件，公共经费与公对公申请均依赖它。 |
| `src/components/RequestDetail.vue` | 采购详情展示组件。 |
| `src/components/ReimbursementDialog.vue` | 报销对话框总入口。 |
| `src/components/PublicEditReimbursementDialog.vue` | 公共经费报销编辑弹窗。 |
| `src/components/C2cEditReimbursementDialog.vue` | 公对公报销编辑弹窗。 |
| `src/components/EditReimbursementDialog.vue` | 旧版报销编辑组件，内部仍有旧接口路径，属于遗留实现。 |
| `src/components/InvoiceFormDialog.vue` | 发票录入/编辑弹窗。 |

#### 小组采购与设备相关组件

| 文件 | 作用 |
| --- | --- |
| `src/components/TeamProcurementForm.vue` | 小组采购申请表单组件。 |
| `src/components/TimeSlotGrid.vue` | 仪器预约时段网格组件。 |
| `src/components/InstrumentBookingView.vue` | 旧版仪器预约组件，与当前 `views/InstrumentBookingView.vue` 功能重叠，偏历史遗留。 |

#### 远程访问子组件

| 文件 | 作用 |
| --- | --- |
| `src/components/remote/RemoteBookingDashboard.vue` | 远程预约主面板，展示机器、预约状态与操作入口。 |
| `src/components/remote/RemoteActiveSession.vue` | 当前活跃远程会话展示与控制。 |

#### Vue 模板残留组件

| 文件 | 作用 |
| --- | --- |
| `src/components/HelloWorld.vue` | Vite/Vue 模板残留。 |
| `src/components/TheWelcome.vue` | Vite/Vue 模板残留。 |
| `src/components/WelcomeItem.vue` | Vite/Vue 模板残留。 |
| `src/components/icons/*` | 模板图标组件，业务中基本不重要。 |

### 5.9 `src/views/` 页面说明

#### 账号与首页

| 文件 | 作用 |
| --- | --- |
| `src/views/LoginView.vue` | 登录页。 |
| `src/views/RegisterView.vue` | 注册页。 |
| `src/views/HomeView.vue` | 首页，聚合公告、项目展示、角色入口等信息。 |
| `src/views/AboutView.vue` | Vue 模板残留页面。 |

#### 采购主流程页面

| 文件 | 作用 |
| --- | --- |
| `src/views/ProcurementRequestView.vue` | 新建采购申请页面。 |
| `src/views/MyRequestsView.vue` | 我的采购申请列表与状态查看。 |
| `src/views/ProcurementApprovalView.vue` | 采购审批总入口，整合多个审批阶段标签页。 |
| `src/views/PaymentView.vue` | 付款视图，存在调用旧驳回接口的问题。 |
| `src/views/InvoiceView.vue` | 发票页面，接口仍指向旧路由，当前更像遗留页面。 |
| `src/views/StatisticsView.vue` | 采购统计/概览页。 |
| `src/views/PlatformManagementView.vue` | 平台管理页面。 |
| `src/views/WhitelistManagementView.vue` | 白名单管理页面。 |
| `src/views/AnnouncementManagementView.vue` | 全局公告管理页面。 |

#### 采购审批流子页面 `src/views/approval_workflow/`

| 文件 | 作用 |
| --- | --- |
| `PublicPendingApprovalTab.vue` | 公共经费待审批列表。 |
| `C2cPendingApprovalTab.vue` | 公对公待审批列表。 |
| `PendingInvoicingTab.vue` | 待开票阶段列表。 |
| `PendingInspectionTab.vue` | 待验收阶段列表。 |
| `PendingReimbursementTab.vue` | 待报销阶段列表，支持合并、撤销合并、附件打包、报销上传。 |

#### 小组采购页面

| 文件 | 作用 |
| --- | --- |
| `src/views/TeamRequestView.vue` | 小组采购申请页面。 |
| `src/views/MyTeamRequestsView.vue` | 我的小组采购申请列表。 |
| `src/views/TeamApprovalView.vue` | 小组采购审批页面。 |
| `src/views/TeamManagementView.vue` | 小组成员/组织管理页面。 |
| `src/views/TeamLedgerView.vue` | 小组采购台账页面。 |

#### 项目、设备、远程访问与显示屏页面

| 文件 | 作用 |
| --- | --- |
| `src/views/ProjectManagementView.vue` | 项目管理与发布页面。 |
| `src/views/InstrumentBookingView.vue` | 仪器预约主页面。 |
| `src/views/InstrumentManagementView.vue` | 仪器管理页面，含时段、早鸟设置，但存在调用未实现日历接口的问题。 |
| `src/views/RemoteBookingView.vue` | 远程主机预约与使用页面。 |
| `src/views/RemoteManagementView.vue` | 远程主机后台管理页面。 |
| `src/views/CorridorScreenManageView.vue` | 走廊显示屏后台管理页面。 |
| `src/views/DisplayPreviewView.vue` | 走廊显示屏公开预览页，还会拉取天气信息。 |

## 6. 数据模型、数据库与 SQL 备份说明

### 6.1 当前运行配置

- 后端默认数据库配置在 `DjangoProject/DjangoProject/settings.py`
- 当前默认数据库名：`new_lab_system`
- 数据库账号、密码、密钥、Guacamole 地址等从环境变量或根目录 `.env` 读取
- 自定义用户模型为：`users.UserProfile`

这意味着：

1. 如果直接启动后端，需要先在本地创建 `new_lab_system`，并在 `.env` 里配置连接信息。
2. 如果导入仓库中的 SQL 备份，很可能要把备份库名从 `lab_system` 调整到 `new_lab_system`，或者反过来修改 `settings.py`。

### 6.2 采购主模型关系

采购主流程的真实关系大致如下：

- `UserProfile` 与 `Role` 是多对多
- `PurchaseRequest` 与 `RequestItem` 是一对多
- `PurchaseRequest` 与 `Invoice` 是一对多
- `PurchaseRequest` 与 `Payment` / `Acceptance` / `Inspection` / `PurchaseOrder` / `Contract` / `ExpenseReport` / `Reimbursement` 是一对一
- `PurchaseRequest.parent_request` 与 `merged_children` 描述合并父子单关系
- `RequestItem.source_request` 与 `original_applicant` 用于撤销合并后的精准回滚

### 6.3 `PurchaseRequest.status` 当前真实状态枚举

当前代码中采购主单状态不是文档想象值，而是以下真实枚举：

- `pending`
- `rejected`
- `withdrawn`
- `payment_rejected`
- `pending_purchase_order`
- `pending_contract`
- `approved`
- `paid`
- `goods_received`
- `invoiced`
- `accepted`
- `inspection_skipped`
- `reimbursed`
- `merged`
- `completed`

其中一个重要实现细节是：

- 前端常说的“待报销”不是数据库原生状态
- 后端实际上把它映射为 `accepted + inspection_skipped`

### 6.4 其他核心业务模型

| 模块 | 主要模型/数据 |
| --- | --- |
| 用户 | `Role`、`UserProfile`、`PasswordResetRequest` |
| 平台与公告 | `Platform`、`WhitelistItem`、`GlobalAnnouncement` |
| 小组采购 | `TeamPurchaseRequest`、`TeamRequestItem` |
| 项目 | `Project` |
| 仪器预约 | `Equipment`、`Booking` |
| 远程访问 | `RdpMachine`、`RdpBooking` |
| 走廊显示屏 | `DisplayImage`、`DisplayConfig` |

### 6.5 SQL 备份文件怎么理解

本机目录里的 `backup_new_data.sql`、`database_backup.sql`、`database_backup_new.sql` 和 `backups/` 都属于 MySQL dump 或历史备份。它们可能覆盖以下几类表：

- `users_*`
- `procurement_*`
- `invoice_invoice`
- `payment_payment`
- `acceptance_acceptance`
- `inspection_inspection`
- `expense_report_*`
- `purchase_order_*`
- `contract_*`
- `reimbursement_*`
- `team_procurement_*`
- `projects_project`
- `equipment_*`
- `remote_access_*`
- `corridor_display_*`

需要注意：

1. 这些 SQL 包含真实用户、邮箱、密码哈希、会话、附件路径等敏感数据，默认不提交到 GitHub。
2. 这些 SQL 是历史时点快照，不保证与当前迁移文件完全一致。
3. 备份中常见库名是 `lab_system`，而运行配置是 `new_lab_system`。
4. 做恢复前最好先对照当前 `models.py` 和迁移文件确认结构是否兼容。
5. 如果只是开发调试，应优先以当前 Django ORM + migrations 为准。

## 7. 当前代码实现出的核心业务流程

### 7.1 公共经费采购流程

实际流程是：

`pending -> paid -> goods_received -> invoiced 或 inspection_skipped -> accepted -> reimbursed`

代码层关键点：

- 审批通过时会要求上传付款截图
- 审批通过后会直接创建 `Payment`
- 收货确认后进入 `goods_received`
- 发票上传后，如果不需要验收可直接进入 `inspection_skipped`
- 验收完成后进入 `accepted`
- 报销提交后进入 `reimbursed`

### 7.2 公对公采购流程

实际流程是：

`pending -> pending_purchase_order -> pending_contract -> paid -> goods_received -> invoiced 或 inspection_skipped -> accepted -> reimbursed`

代码层关键点：

- 审批后不会直接完结，而是进入请购单/合同链路
- 支持 `submit-links`
- 支持 `skip_purchase_order`
- 支持 `skip_contract`

### 7.3 合并报销与撤销合并

这是当前项目里比较复杂、也比较有特色的一段逻辑。

- 合并接口：`/api/procurement/merge-requests/`
- 撤销合并接口：`/api/procurement/requests/{id}/unmerge/`
- 允许合并的阶段：
  - `invoiced`
  - `accepted`
  - `inspection_skipped`
- 合并时：
  - 创建父单
  - 子单状态改为 `merged`
  - 子单明细迁移到父单
  - 保留原申请来源与原申请人
- 撤销时：
  - 依赖 `merged_from_status`、`source_request`、`original_applicant`
  - 把子单恢复到合并前状态

### 7.4 小组采购流程

小组采购是独立于主采购流程的轻量版采购流。

- 申请人提交小组采购单
- 小组管理员审批
- 台账统一查询
- 当前模型状态仅有 `pending / approved / rejected / completed / withdrawn`

### 7.5 仪器预约流程

- 管理员配置仪器、开放时段、预约规则、早鸟策略
- 普通用户查看可预约时段
- 用户提交预约、查看历史、取消预约
- 早鸟用户可享受不同提前预约窗口

### 7.6 远程访问流程

- 管理员维护 `RdpMachine`
- 用户预约远程主机时段
- 到时可连接、断开、上报状态
- 支持活跃会话显示
- 支持插队申请与审批
- 支持设备端自动登录

### 7.7 走廊显示屏流程

- 管理员上传并排序展示图片
- 管理员调整展示配置
- 前端公开页拉取 `/api/corridor_display/public/`
- 显示屏页面据此展示图片、公告、天气等内容

## 8. API 前缀总览

当前后端统一通过 `/api/` 暴露接口，主要前缀如下：

- `/api/users/`
- `/api/procurement/`
- `/api/projects/`
- `/api/invoice/`
- `/api/payment/`
- `/api/acceptance/`
- `/api/inspection/`
- `/api/expense-reports/`
- `/api/reimbursement/`
- `/api/purchase-orders/`
- `/api/contracts/`
- `/api/team-procurement/`
- `/api/equipment/`
- `/api/remote_access/`
- `/api/corridor_display/`
- `/api/token/`
- `/api/token/refresh/`

## 9. 文档、截图与历史记录文件说明

| 路径 | 说明 |
| --- | --- |
| `Procurement_process_readme.md` | 采购流程历史文档，适合快速理解业务，但要以当前代码和本 README 为准。 |
| `远程连接readme.md` | 远程连接功能背景资料。 |
| `改动内容.md` | 历史改动清单，可辅助理解某些代码为什么这么写。 |
| `粘贴.md` | 历史修复脚本记录，尤其与采购合并数据修复有关。 |
| `problem3_child.png` / `problem3_crop.png` / `problem3_top.png` | 历史问题截图。 |

## 10. 已确认的前后端不一致与技术债

这部分不是“猜测”，而是从当前代码直接能看出来的差异。

### 10.1 前后端接口不一致

1. `PaymentView.vue` 仍调用旧接口：
   - 前端调用：`/procurement/purchase-requests/{id}/reject_payment/`
   - 后端实际接口：`/payment/purchase-requests/{id}/reject/`
2. `InvoiceView.vue` 仍使用旧发票列表接口：
   - 前端调用：`/invoice/full-info-requests/`
   - 后端当前保留的是：`/invoice/invoices/`
3. `InstrumentManagementView.vue` 调用了不存在的接口：
   - 前端调用：`/equipment/equipments/{id}/calendar/`
   - 后端未实现该路由

### 10.2 状态枚举不一致

`team_procurement` 模块的 `TeamPurchaseRequest.STATUS_CHOICES` 只有：

- `pending`
- `approved`
- `rejected`
- `completed`
- `withdrawn`

但对应台账视图仍在用 `paid / ordered / invoiced / accepted` 等状态筛选，说明该模块仍有历史代码未清理干净。

### 10.3 遗留页面与模板残留

- `src/components/EditReimbursementDialog.vue` 仍有旧采购接口路径
- `src/components/InstrumentBookingView.vue` 与实际页面版仪器预约实现重叠
- `src/components/HelloWorld.vue`、`TheWelcome.vue`、`WelcomeItem.vue`
- `src/views/AboutView.vue`
- `src/stores/counter.js`

以上文件更接近模板残留或旧实现，不属于当前主业务路径。

### 10.4 依赖声明不完整

实际代码中多处使用了 `lodash-es`，但 `frontend/package.json` 当前没有声明该依赖。  
如果重新安装前端依赖后出现运行错误，需要补充安装并写回依赖清单。

### 10.5 后端工程化不足

- 各 app `tests.py` 基本未形成有效测试
- 生产环境仍需要单独配置真实密钥、数据库密码、域名、反向代理与备份策略

这意味着当前项目更偏“可运行业务系统”，但工程化与可迁移性仍有提升空间。
