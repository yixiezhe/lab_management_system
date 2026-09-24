# 可选 Guacamole 接入

默认 Compose 仅启动核心业务和可选 RAG，不启动远程桌面。
Django remote_access 源码及迁移保留，因为设备模型依赖远程主机表；
不接入远程主机时这些表可以为空。

## 新部署指引

先阅读 [Guacamole Docker 官方说明](https://guacamole.apache.org/doc/1.5.5/gug/guacamole-docker.html)。
这是历史集成版本的部署说明，不代表该旧版本适合直接对公网提供服务；
新部署需要单独评估版本升级与兼容性。

需要自行部署 guacd、Guacamole Web 和专用认证数据库。
使用同一发行版本的官方镜像生成新库结构，例如：

```sh
docker run --rm guacamole/guacamole:1.5.5 /opt/guacamole/bin/initdb.sh --postgresql > initdb.sql
```

只把生成的结构导入新的专用数据库，不要导入本系统实际 Guacamole 数据库。
按官方说明配置数据库连接和 GUACD_HOSTNAME。
数据库和 guacd 不直接暴露到不可信网络；Guacamole Web 初次部署仅绑定本机端口。
首次初始化后立即更换官方默认管理员密码，再接入系统。

Django 环境变量：

```dotenv
GUACAMOLE_URL=http://localhost:8080/guacamole
GUACAMOLE_INTERNAL_API_URL=http://guacamole:8080/guacamole/api
GUAC_ADMIN_USER=guacadmin
GUAC_ADMIN_PASSWORD=
```

GUACAMOLE_URL 是浏览器可访问地址，INTERNAL_API_URL 是后端容器可访问地址；
两者不一定相同。示例内部域名 guacamole 需要在你自己的 Docker 网络中配置。
FERNET_KEY 用于远程密码加密，必须自行生成并安全备份；不要随意更换已在使用的密钥。

## 不包含的部署资产

- 真实主机地址、系统密码、Guacamole 用户与连接数据。
- 来源/再分发权限未确认的自定义剪贴板补丁 JAR。
- 依赖该补丁的 custom_start.sh。
- Windows 被控端完整自动登录/锁屏/解控脚本。

因此，仅启动官方镜像不等于复现历史部署的全部设备端增强功能。
需要这些增强功能时，应先补齐源码、许可、配置模板及安全审查，再作为独立可选组件发布。
