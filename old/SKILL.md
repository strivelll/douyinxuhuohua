---
name: batch-douyin-huohua
description: >-
  批量检测抖音私信列表中的联系人，向所有已熄火花的好友发送激活消息以维持火花。
  v8: 模块化重构，多级降级选择器，登录态检测，飞书推送，定时调度。
---

# Batch Douyin Huohua v8

## Quick Start

```bash
# 首次使用: 先通过正常浏览器登录抖音，Profile 会保存在 ./profile/
# 扫描模式（不发消息，测试用）
cd /root/batch-douyin-huohua
DISPLAY=:10 python3 -m src --dry-run

# 正常执行
DISPLAY=:10 python3 -m src

# 自定义消息
DISPLAY=:10 python3 -m src --message "早安续火"

# 安装每日定时（默认 9:00 AM）
DISPLAY=:10 python3 -m src --install-cron

# 配置飞书推送（执行结果推送到群机器人）
# 编辑 .env 文件，填入 HUOHUA_FEISHU_WEBHOOK
```

## 架构

```
src/
├── __main__.py        CLI 入口 (argparse)
├── browser.py         浏览器生命周期（启动/清理/反检测）
├── selectors.py       多级降级选择器系统
├── navigation.py      页面导航（弹窗/私信面板/返回）
├── contacts.py        联系人扫描 + 火花检测
├── messenger.py       消息发送 + 发送确认
├── auth.py            登录态检测
├── robustness.py      重试/截图/超时工具
├── scheduler.py       crontab 安装/移除
├── report.py          报告输出
└── notifier.py        飞书 Webhook 推送
```

## 关键改进 (v7 → v8)

| 改进项 | v7 | v8 |
|--------|-----|-----|
| 选择器策略 | 单级 minified class | 多级降级 (data-e2e → text → TreeWalker → 坐标) |
| 登录检测 | 无 | 运行前检查 avatar/cookie，未登录报错不盲跑 |
| 弹窗处理 | 仅"取消"按钮 | 循环关闭多类型弹窗 |
| 发送确认 | 无 | 检查输入框清空 + 消息气泡匹配 |
| 错误恢复 | 无 | 指数退避重试 + 失败截图 |
| 配置 | 硬编码 | pydantic-settings (CLI > .env > YAML > 默认值) |
| 通知 | 无 | 飞书群机器人推送 |
| 调度 | 无 | cron 安装/移除 (flock 防并发) |

## 火花检测

| 状态 | 检测规则 | 行为 |
|------|---------|------|
| 🔥 活跃 | img[src*="chat_days"] 且 src **不包含** disable | **跳过** |
| 💤 已熄 | img[src*="chat_days"] 且 src 包含 disable | **发送** |
| ⚠️ 将熄 | img[src*="chat_days"] 且 src 包含 warning/expire | **跳过**（仅为信息） |
| 💀 无火花 | 无 chat_days 图片 | **跳过** |