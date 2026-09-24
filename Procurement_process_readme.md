# 采购流程说明（公共经费 / 公对公）

本文件聚焦“公共经费采购流程”和“公对公采购流程”，基于当前前后端源码与接口梳理。  
若要了解项目全貌，请先阅读根目录 `README.md`。

---

## 1. 角色与职责（与采购流程相关）
- 申请人：提交采购申请、在付款后确认收货。
- 采购人员：公共经费审批与流程处理人（`handler`），负责后续流程推进。
- 导师用户：可审批公共经费，且可管理组内团队采购授权。
- 系统管理员：拥有所有权限；可批量删除采购单等。
- 付款人：管理付款截图、可驳回“已批准”的采购申请。
- 大总管：平台管理与白名单维护权限。
- 公对公平台负责人：通过 `Platform.managers` 赋权，可审批所负责的平台请求。
- 项目管理员：与公告/项目发布相关，不直接参与采购流转。
- 小组采购人员：用于团队采购模块，与公共/公对公主流程分离。

---

## 2. 核心数据模型（简要）
- `PurchaseRequest`：采购单主表，含 `expense_type`、`platform`、`status`、`order_number`、`handler` 等。
- `RequestItem`：采购明细项（内容、规格、数量、单价、采购链接等）。
- `Platform`：平台配置（类别、前缀、负责人）。
- `WhitelistItem`：采购白名单（内容、平台、类型等）。
- `Payment`：付款截图（公共经费审批/付款环节）。
- `Acceptance`：收货确认（收货描述 + 收货照片）。
- `Invoice`：发票信息（发票号、公司、截图、是否需验收）。
- `Inspection`：验收信息（验收单号、验收照片）。
- `PurchaseOrder`：请购单文件（公对公流程）。
- `Contract`：合同文件（公对公流程）。
- `Reimbursement`：报销凭证（报销单号 + 照片）。

---

## 3. 状态机总览
### 3.1 公共经费主路径
`pending` → `paid` → `goods_received` → `invoiced`/`inspection_skipped` → `accepted` → `reimbursed`

### 3.2 公对公主路径
`pending` → `pending_purchase_order` → `pending_contract` → `paid` → `goods_received` → `invoiced`/`inspection_skipped` → `accepted` → `reimbursed`

### 3.3 例外/中间状态
`rejected`（审批驳回）、`withdrawn`（申请人撤回）、`payment_rejected`（付款人驳回）、`merged`（已合并）、`completed`（完成）

---

## 4. 公共经费采购流程（详细）

### 4.1 申请入口与限制
页面：`/procurement/request`（`ProcurementRequestView.vue`）  
时间限制：仅 8:00–19:30 可提交（前端限制）。

### 4.2 填写申请（`ProcurementForm.vue`）
1) 选择经费类型：公共经费  
2) 选择平台（来自 `/procurement/platforms/`）  
3) 选择采购类型（耗材/药品）  
4) 从白名单选择采购内容  
5) 填写明细项：
   - **公共经费必须填写采购链接**
   - 部分平台（如“多多/药代”）要求填写规格
   - 自动计算总价  
6) 支持草稿自动保存（LocalStorage）
> 前端会在公共经费表单与审批页展示“值班采购人员”提示（仅提示，不改变流程规则）。

提交接口：
- 创建：`POST /api/procurement/public-purchase-requests/`
- 编辑：`PATCH /api/procurement/public-purchase-requests/{id}/`

初始状态：`pending`

### 4.3 审批（公共经费）
页面：`/approval/public-funding` → `PublicPendingApprovalTab.vue`  
可审批角色：采购人员 / 导师用户 / 系统管理员  
审批动作：
- **批准**：必须上传付款截图  
  - 接口：`POST /api/procurement/public-purchase-requests/{id}/approve/`
  - 生成单号（平台前缀 + 日期 + 序号）
  - 写入 `Payment` 记录
  - 状态变为 `paid`
- **驳回**：填写原因  
  - 接口：`POST /api/procurement/public-purchase-requests/{id}/reject/`
  - 状态变为 `rejected`

### 4.4 付款管理（付款人）
页面：`/payment`（`PaymentView.vue`）  
角色：付款人  
作用：
- 对 `approved/paid` 的申请上传/修改付款截图
- 可驳回已批准申请 → 状态变为 `payment_rejected`（回到审批）
接口：
- 付款截图：`POST /api/payment/payments/` 或 `PATCH /api/payment/payments/{id}/`
- 付款驳回：`POST /api/payment/purchase-requests/{id}/reject/`

### 4.5 申请人确认收货
页面：`/my-requests`（`MyRequestsView.vue`）  
条件：仅申请人，且状态为 `paid`  
操作：
1) 填写收货情况
2) 上传收货照片  
接口：
- `POST /api/acceptance/acceptances/`

状态变化：`paid` → `goods_received`

### 4.6 开票（发票信息录入）
页面：审批中心 → “待开票”  
条件：状态为 `goods_received`  
操作：
1) 填写发票号/公司  
2) 上传发票截图  
3) 选择“是否需验收”

接口：
- `POST /api/invoice/invoices/` 或 `PATCH /api/invoice/invoices/{id}/`

状态变化（由后端信号处理）：
- `requires_acceptance = true` → `invoiced`
- `requires_acceptance = false` → `inspection_skipped`

> 前端会根据金额/单价给出验收建议；最终以提交字段为准。

### 4.7 验收（如需）
页面：审批中心 → “待验收”  
条件：状态为 `invoiced`  
操作：
1) 填写验收单号
2) 上传验收照片  
接口：
- `POST /api/inspection/inspections/` 或 `PATCH /api/inspection/inspections/{id}/`

状态变化：`invoiced` → `accepted`

> 后端另提供 `skip_inspection` API，可直接跳过验收。

### 4.8 报销资料完善（可编辑）
页面：审批中心 → “待报销”（`PendingReimbursementTab.vue`）  
可编辑内容（公共经费）：
- 付款截图 / 发票信息 / 验收信息
- 合并单支持对子项分别维护付款与发票

接口：
- `POST /api/procurement/public-purchase-requests/{id}/update-reimbursement-details/`

### 4.9 报销凭证上传
页面：审批中心 → “待报销”  
操作：填写报销单号 + 上传报销照片  
接口：
- `POST /api/reimbursement/reimbursements/`

状态变化：`accepted`/`inspection_skipped` → `reimbursed`

### 4.10 对账 / 合并 / 打包
页面：  
`/ledger/public`、审批中心“待验收/待报销”  
功能：
- 合并多个“待验收”申请为父单  
  - 接口：`POST /api/procurement/merge-requests/`
- 打包附件（单个或批量）
  - `GET /api/procurement/requests/{id}/package-attachments/`
  - `POST /api/procurement/package-receipts/`
- 管理员批量删除
  - `POST /api/procurement/bulk-delete-requests/`

---

## 5. 公对公采购流程（详细）

### 5.1 提交申请
入口与公共经费相同，但经费类型选择 **公对公**。  
区别点：
- 采购链接 **可不填**（后续可由采购人员补录）
- 状态初始为 `pending`

提交接口：
`POST /api/procurement/c2c-purchase-requests/`

### 5.2 审批（公对公）
页面：`/approval/c2c`  
可审批角色：
系统管理员 / 导师 / 公对公平台负责人  
审批动作：
1) 批准 → 生成单号 → 状态变为 `pending_purchase_order`  
2) 驳回 → 状态变为 `rejected`

接口：
- `POST /api/procurement/c2c-purchase-requests/{id}/approve/`
- `POST /api/procurement/c2c-purchase-requests/{id}/reject/`

### 5.3 请购单阶段（`pending_purchase_order`）
页面：审批中心 → “待请购”  
操作：
- 上传请购单（`PurchaseOrder`）
  - `POST /api/purchase-orders/purchase-orders/`
  - 状态变为 `pending_contract`
- 或跳过请购单
  - `POST /api/procurement/c2c-purchase-requests/{id}/skip_purchase_order/`

### 5.4 合同阶段（`pending_contract`）
页面：审批中心 → “待合同”  
操作：
- 上传合同（`Contract`）
  - `POST /api/contracts/contracts/`
  - 状态变为 `paid`
- 或跳过合同
  - `POST /api/procurement/c2c-purchase-requests/{id}/skip_contract/`

### 5.5 采购链接补录（可选）
后端提供：
`POST /api/procurement/c2c-purchase-requests/{id}/submit-links/`  
用于在请购阶段补录每个 `RequestItem` 的采购链接。

### 5.6 付款后收货、发票、验收、报销
后续流程与公共经费一致：
`paid` → `goods_received` → `invoiced`/`inspection_skipped` → `accepted` → `reimbursed`  
区别点：
- 公对公报销信息编辑中，支持 **请购单** 与 **合同** 的补传/修改。
- 新建发票时默认 `requires_acceptance = true`（需验收）。

---

## 6. 关键校验与规则
- **平台前缀**必须配置，否则无法生成订单号（审批会失败）。
- 公共经费申请必须填写 **采购链接**。
- 特定平台需要填写规格字段（如“多多/药代”）。
- 申请人仅可编辑 `pending` / `rejected` 的申请。
- 申请人可在 `pending` 状态撤回（`withdrawn`）。
- 付款人驳回将状态置为 `payment_rejected`，回到审批环节。
- 合并操作仅允许“待验收（invoiced）”且未合并的同类经费申请。

---

## 7. 页面与接口对照（速查）
| 阶段 | 公共经费 | 公对公 |
|---|---|---|
| 申请提交 | `/procurement/request` → `POST /procurement/public-purchase-requests/` | `/procurement/request` → `POST /procurement/c2c-purchase-requests/` |
| 审批 | `/approval/public-funding` → `/public-purchase-requests/{id}/approve/` | `/approval/c2c` → `/c2c-purchase-requests/{id}/approve/` |
| 请购单 | - | `/purchase-orders/purchase-orders/` |
| 合同 | - | `/contracts/contracts/` |
| 收货 | `/my-requests` → `/acceptance/acceptances/` | 同左 |
| 发票 | `/approval/*` → `/invoice/invoices/` | 同左 |
| 验收 | `/approval/*` → `/inspection/inspections/` | 同左 |
| 报销 | `/approval/*` → `/reimbursement/reimbursements/` | 同左 |

---

## 8. 参考截图
- `截图/公共经费采购流程--待报销页面截图.png`
