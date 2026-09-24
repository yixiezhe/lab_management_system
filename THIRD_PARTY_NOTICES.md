# 第三方组件与发布边界

此文件是组件来源索引，不替代各组件许可证，也不代表已经完成法律或依赖审计。
主项目许可证待所有者确认；在此之前，本分支仅作为私有发布准备材料。

## 依赖

Python 依赖见 DjangoProject/requirements.txt；前端依赖与锁定版本见
frontend/package.json 和 frontend/package-lock.json。
Docker 镜像名称和摘要见 Compose 与 Dockerfile。
依赖的版本、许可证、许可证附带条件及已知漏洞应在公开前逐项核验；
本仓库不打包 node_modules、Python/Conda 环境或容器镜像本体。

## Apache Guacamole

远程桌面集成使用 Apache Guacamole。
其上游代码采用 Apache License 2.0，若再分发上游文件、修改版本或二进制，
必须根据实际分发范围保留所需许可与 NOTICE。
参见 [上游 LICENSE](https://github.com/apache/guacamole-client/blob/main/LICENSE)。
本准备快照保留集成源码，不携带上游数据库初始化 SQL 或自定义 JAR 二进制。
官方镜像由使用者自行获取。

历史部署中的自定义剪贴板补丁 JAR 未确认来源、构建源码及再分发权利，暂不包含；
不得将它描述为本仓库已经提供的可复现开源实现。
被控 Windows 主机上的自动登录、锁屏/解控等端侧脚本未在本次项目源码范围内找到完整实现，
不在本次发布范围；仓库中的 scripts/ 主要是服务启停/备份辅助脚本。

## 模型与内容

BGE-M3、Ollama 模型、商业模型服务需遵守各自模型许可证及服务条款。
本仓库不附带模型权重、模型 API 密钥或第三方账号。
实验室照片、机构 Logo、真实成员信息、账务数据和附件未包含在此快照。
演示 SVG 和示例数据为本次准备时生成的通用虚构内容。
