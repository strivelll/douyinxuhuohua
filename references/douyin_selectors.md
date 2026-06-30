# 抖音关键 DOM 选择器参考

> 抖音页面结构频繁更新，此处记录已知的选择器模式。
> 脚本内含多级降级策略，当前选择器失效时会自动尝试下一级。

## 首页

| 目标 | 选择器模式 | 说明 |
|------|-----------|------|
| 用户头像（已登录） | `div[class*="avatar"]`, `span[class*="user-info"]` | 检测登录态的探针 |
| 登录按钮（未登录） | `div[class*="login"]`, `button:has-text("登录")` | 未登录标志 |
| 搜索框 | `input[class*="search"]` | 抖音顶部搜索 |

## 私信/消息图标

| 选择器 | 说明 |
|--------|------|
| `div[class*="header"] a[href*="notify"]` | Header 内通知链接 |
| `div[class*="header"] *[class*="message"]` | Header 消息图标 |
| `div[class*="header"] *[class*="letter"]` | Header 私信图标 |
| `svg[class*="message"]` | 通用消息 SVG |
| `div[class*="header"] div:has(svg)` | 兜底：任何带 SVG 的 header 元素 |

## 下拉私信列表

| 选择器 | 说明 |
|--------|------|
| `div[class*="dropdown"]` | 下拉弹窗容器 |
| `div[class*="popover"]` / `div[class*="popper"]` | 通用 popover 弹窗 |
| `div[class*="chat-item"]` | 单个聊天条目 |
| `div[class*="session-item"]` | 会话条目 |
| `div[class*="im-item"]` | IM 联系人条目 |

## 联系人条目内

| 选择器 | 说明 |
|--------|------|
| `span[class*="name"]` | 联系人昵称 |
| `div[class*="name"]` | 昵称备选 |
| `span[class*="nick"]` | 昵称备选 |
| `🔥`（文本） | 火花 emoji 标志 |
| `svg[class*="fire"]` | 火花 SVG 图标 |

## 聊天窗口

| 选择器 | 说明 |
|--------|------|
| `div[contenteditable="true"]` | 聊天输入框（富文本） |
| `textarea` | 输入框备选 |
| `button:has-text("发送")` | 发送按钮 |
| `div[class*="send-btn"]` | 发送按钮备选 |
| `div[class*="message"]:last-child` | 最后一条消息（发送确认用） |

## 调试建议

如果脚本在选择器上失效，可以在浏览器控制台调试：

```javascript
// 查看头部所有元素
document.querySelector('div[class*="header"]').children

// 查看所有 SVG
document.querySelectorAll('svg')

// 查看所有弹窗/下拉
document.querySelectorAll('div[class*="dropdown"], div[class*="popover"]')

// 查看联系人列表
document.querySelectorAll('[class*="chat-item"], [class*="session-item"]')
```

## 常见变更模式

抖音前端经常进行 A/B 测试，以下是已知的 DOM 结构变更模式：

1. `class*="im-*"` → `class*="chat-*"` 类名全量替换
2. 消息面板从弹出层 → 独立页面 → 侧边栏
3. SVG 图标从内联 → 外链 → `<use>` 引用
4. 火花状态从 emoji → 图片 → 特定 CSS class
