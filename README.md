# 抖音续火花 (Douyin Huohua)

自动检测抖音私信列表中的「火花」状态，对已熄灭火花的好友发送消息。

## 功能

- 登录态检测 — 未登录提前报错，不盲跑
- 多级选择器降级 — data-e2e → 文本匹配 → TreeWalker → 坐标兜底
- 智能弹窗关闭 — 循环消除多种弹窗
- 火花状态分类 — 活跃/已熄/将熄/无火花
- 定时执行 — 内置 cron 安装/移除，flock 防并发
- 飞书通知 — 执行结果推送飞书群机器人
- 失败截图 — 异常自动截图留档

## 快速开始

```bash
# 1. 安装依赖
pip install playwright pydantic-settings PyYAML
playwright install chromium

# 2. 配置飞书 Webhook（用于接收执行结果）
cp .env.example .env
# 编辑 .env，填入 HUOHUA_FEISHU_WEBHOOK

# 3. 登录抖音（首次需要）
# 用一个有图形界面的方式先登录，profile 会保存在 ./profile/

# 4. 试运行（不发送消息）
python -m src --dry-run

# 5. 跑一次
python -m src

# 6. 安装每日定时任务
python -m src --install-cron
```

## 配置

通过环境变量或 `.env` 文件配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HUOHUA_FEISHU_WEBHOOK` | (必填) | 飞书机器人 Webhook URL |
| `HUOHUA_MESSAGE_DEFAULT` | 🔥 | 默认发送消息 |
| `HUOHUA_CRON_EXPRESSION` | `0 9 * * *` | cron 表达式 |
| `HUOHUA_PROFILE_DIR` | `./profile` | 浏览器 Profile 目录 |
| `HUOHUA_SCREENSHOT_DIR` | `./screenshots` | 截图保存目录 |

## 项目结构

```
src/
├── __main__.py        CLI 入口（argparse）
├── browser.py         浏览器生命周期（启动/清理/反检测）
├── selectors.py       多级降级选择器
├── navigation.py      页面导航（弹窗/私信面板）
├── contacts.py        联系人扫描 + 火花检测
├── messenger.py       消息发送
├── auth.py            登录态检测
├── robustness.py      重试/截图/超时工具
├── scheduler.py       crontab 安装/移除
├── report.py          执行报告
├── notifier.py        飞书 Webhook 推送
└── report.py          报告输出
```

## 火花检测规则

| 状态 | 检测规则 | 操作 |
|------|---------|------|
| 🔥 活跃 | `img[src*="chat_days"]` 且非 disable | 跳过 |
| 💤 已熄 | `img[src*="chat_days"]` 含 disable | 发送消息 |
| ⚠️ 将熄 | `img[src*="chat_days"]` 含 warning/expire | 跳过 |
| 💀 无火花 | 无 `chat_days` 图片 | 跳过 |
