# Railway 部署说明（Flask + MySQL）

## 1. 推送代码到 GitHub

将 `ProjectonWeb` 目录作为一个仓库（或子目录）推送到 GitHub。

## 2. 在 Railway 创建项目

1. 登录 Railway
2. 点击 `New Project` -> `Deploy from GitHub repo`
3. 选择你的仓库

Railway 会自动识别 `Dockerfile` 并构建服务。

## 3. 创建 MySQL 服务

1. 在同一个 Railway Project 内点击 `New` -> `Database` -> `MySQL`
2. 等待数据库创建完成

## 4. 配置环境变量

在 Web 服务的 Variables 中设置：

- `SECRET_KEY`：任意随机字符串
- `DATABASE_URL`：建议直接粘贴 MySQL 服务提供的连接串

如果你的数据库不是 Railway 内置 MySQL，也可设置：

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`

## 5. 初始化数据库

将 `tradingplat.sql` 导入到目标数据库中，确保有：

- `user`
- `item`
- `orders`

三张表及初始数据。

## 6. 检查部署日志

部署成功日志应出现 Gunicorn 启动信息（无 traceback）。

若出现 500：

- 先看连接错误（host/port/user/password/dbname）
- 再看是否缺表（`Table ... doesn't exist`）
- 再看是否环境变量名配置错误

## 7. 发布域名

在 Settings / Networking 中生成公网域名，访问即可在线使用。
