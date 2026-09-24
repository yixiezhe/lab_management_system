# 远程连接模块说明（remote_access）

本说明文档聚焦系统中“远程连接/远程主机预约”相关功能，包括后端 remote_access 应用、前端远程连接页面与管理页面、权限与流程、以及与 Guacamole/本机模式（kiosk）协作的细节。

---

## 1. 功能概览

远程连接模块提供以下能力：
- 远程主机资源管理（系统管理员）：新增/编辑/删除主机、启用/禁用。
- 普通用户预约与连接：选择主机、查看占用状态、创建预约、进入远程连接。
- 会话状态与心跳：实时显示剩余时长、自动结束超时会话。
- 紧急插队（Takeover）：占用中可申请插队，被占用方可同意/拒绝。
- 本机模式（kiosk/land 设备主机）：在“本机自连”场景下避免真正 RDP 连接，改为本机占用流程。

---

## 2. 角色与权限

### 2.1 系统管理员
- 可访问“远程主机管理”页面。
- 拥有远程主机全量 CRUD 权限。

### 2.2 普通登录用户
- 可访问“远程主机预约”页面。
- 仅能查看启用状态的主机列表。
- 只能查看/管理自己的预约记录。

### 2.3 land 设备主机账号（Land Host）
- 前端路由层面限制：只能访问 `/remote-booking`、`/display-preview` 等白名单路径。
- 主要用于固定设备/机位自连场景；在前端会被识别为“本机模式”。

---

## 3. 后端核心模块（Django: remote_access）

### 3.1 数据模型

#### RdpMachine（远程主机）
- `name`: 主机名称（唯一）
- `ip_address`: IP/域名
- `guacamole_id`: Guacamole 连接 ID（用于匹配连接）
- `description`: 描述
- `is_active`: 是否启用
- `username`: Windows 用户名
- `encrypted_password`: 加密后的密码（通过 FERNET_KEY 加密）

> 密码写入通过 `password` 属性自动加密存储，读取时解密；解密失败会返回 `DECRYPTION_ERROR`。

#### RdpBooking（预约记录）
- `user`: 预约用户
- `machine`: 预约的主机
- `start_time / end_time`: 预约时间段
- `status`: `confirmed | active | completed | canceled`
- `real_end_time`: 实际结束时间
- `termination_reason`: `normal | forced | takeover`
- 插队相关：
  - `takeover_applicant`
  - `takeover_requested_at`
  - `takeover_status`: `none | pending | approved | rejected`

**冲突校验**：`clean()` 中会判断时间段是否重叠，重叠则拒绝。

### 3.2 视图与业务逻辑

#### RdpMachineViewSet
- 列表：管理员看到全部；普通用户仅看到 `is_active=True`。
- `current_status`：返回占用状态、占用用户、是否为本人预约、插队状态等。

#### RdpBookingViewSet
- `create`：创建预约（默认 `confirmed`），冲突校验。
- `my`：查询“我的预约”，支持日期过滤（按北京时间当天范围）。
- `cancel`：只能取消 `confirmed` 状态。
- `connect`：
  - 校验时间窗口（允许开始前 5 分钟）。
  - 调用 Guacamole 内部 API，生成连接 URL。
  - 将 `confirmed` 状态更新为 `active`。
- `disconnect`：主动结束，标记 `completed` + `normal`。
- `check_status`：心跳检测。
  - 超时自动结束并 `forced`。
  - 插队等待超过 60 秒自动同意并 `takeover`。
- `request_takeover` / `approve_takeover` / `reject_takeover`：插队请求/处理。

---

## 4. 前端功能结构

### 4.1 页面入口
- `RemoteBookingView.vue`：远程主机预约页
- `RemoteManagementView.vue`：远程主机管理页（系统管理员）

### 4.2 远程预约页结构

#### RemoteBookingDashboard
- 选择主机、查看占用状态
- 占用时可申请紧急插队
- 空闲时“立即连接”（创建 2 小时预约并进入连接）
- 我的连接记录（按日期查询，支持取消）

#### RemoteActiveSession
- 进入远程连接（Guacamole iframe）
- 心跳检测（每 5 秒）
- 剩余时间与超时提醒
- 插队请求提醒（可同意/拒绝）
- 支持全屏、剪贴板同步
- **本机模式（kiosk）**：
  - 通过 URL `kiosk_mode=true` 或 localhost 判断
  - 不调用 `connect`，避免真正 RDP 连接导致锁屏
  - 使用 AHK 触发最小化/锁屏动作

---

## 5. API 接口汇总（remote_access）

> 以 `apiClient` 配置的 baseURL 为前缀，下面仅列路径。

### 主机管理
- `GET /remote_access/machines/` 获取主机列表
- `GET /remote_access/machines/{id}/current_status/` 获取当前占用状态
- `POST /remote_access/machines/` 新增主机（系统管理员）
- `PUT /remote_access/machines/{id}/` 更新主机（系统管理员）
- `DELETE /remote_access/machines/{id}/` 删除主机（系统管理员）

### 预约与连接
- `GET /remote_access/bookings/my/?date=YYYY-MM-DD` 获取“我的预约”
- `POST /remote_access/bookings/` 创建预约
- `POST /remote_access/bookings/{id}/cancel/` 取消预约
- `POST /remote_access/bookings/{id}/connect/` 获取连接 URL（进入会话）
- `POST /remote_access/bookings/{id}/disconnect/` 主动登出
- `GET /remote_access/bookings/{id}/check_status/` 心跳检查

### 插队（紧急占用）
- `POST /remote_access/bookings/{id}/request_takeover/` 申请插队
- `POST /remote_access/bookings/{id}/approve_takeover/` 同意插队
- `POST /remote_access/bookings/{id}/reject_takeover/` 拒绝插队

---

## 6. 典型流程

### 6.1 普通远程连接
1. 用户进入“远程主机预约”页，选择主机。
2. 若主机空闲，点击“立即连接”。
3. 后端创建预约（confirmed），前端调用 connect，进入 active。
4. 前端进入 RemoteActiveSession，开始心跳。
5. 用户结束会话，调用 disconnect，状态变为 completed。

### 6.2 插队流程
1. 主机被占用，用户点击“申请紧急插队”。
2. 被占用方收到插队提示，可同意或拒绝。
3. 超过 60 秒未响应，后端自动同意插队并强制释放。

### 6.3 本机模式（kiosk）
1. 设备以 `kiosk_mode=true` 或 localhost 访问远程预约页。
2. 进入会话时判断为“本机模式”。
3. 不调用 connect，只进行本机模式占用与心跳。

---

## 7. 配置与依赖

### 7.1 Guacamole
- 后端通过环境变量或根目录 `.env` 配置：
  - `GUACAMOLE_PUBLIC_URL`
  - `GUACAMOLE_INTERNAL_API_URL`
  - `GUAC_ADMIN_USER / GUAC_ADMIN_PASSWORD`
  - `GUAC_AUTH_PROVIDER`
- 连接 URL 会根据主机名称匹配 Guacamole 连接树中的连接。

### 7.2 密码加密
- `FERNET_KEY` 必须在环境变量或根目录 `.env` 中正确配置。
- 主机密码存储为加密字符串。

### 7.3 时区
- 预约列表 `my` 接口按北京时区过滤当天数据。

---

## 8. 关键注意事项

- 预约时间段冲突会被后端直接拒绝。
- 预约状态变化依赖 connect/disconnect/heartbeat 等逻辑驱动。
- “本机模式”避免真实 RDP 连接导致自锁屏，需配合 AHK 脚本或本地环境配置。
- land 设备主机账号会被路由限制，仅能访问远程预约相关页面。

---

## 9. 相关源码路径

后端：
- `DjangoProject/remote_access/models.py`
- `DjangoProject/remote_access/serializers.py`
- `DjangoProject/remote_access/views.py`
- `DjangoProject/remote_access/permissions.py`
- `DjangoProject/remote_access/urls.py`

前端：
- `frontend/src/views/RemoteBookingView.vue`
- `frontend/src/components/remote/RemoteBookingDashboard.vue`
- `frontend/src/components/remote/RemoteActiveSession.vue`
- `frontend/src/views/RemoteManagementView.vue`
- `frontend/src/api/remote_access.js`
- `frontend/src/router/index.js`

---

如需扩展功能（例如：预约时间段自定义、管理员强制断开、主机分组/标签等），可在以上路径基础上继续拓展。
