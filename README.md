# UUID Generator

免费的中英文 UUID v4 生成工具。支持每次生成 1～100 个、逐个复制和全部复制，结果在浏览器中生成，不上传或保存。

## 在电脑上预览

在项目文件夹的 PowerShell 中执行：

```powershell
npx.cmd --yes serve public --listen 3000
```

打开 `http://localhost:3000/` 或 `http://localhost:3000/zh/`。按 `Ctrl+C` 停止预览。

## 发布

使用 HTML、CSS、JavaScript，无框架、数据库或构建依赖。Vercel 发布目录为 `public`，框架选择 `Other`，构建命令留空；配置已写在 `vercel.json`。

完整执行步骤见《02-部署执行文档.md》。代码现已实现，开发步骤已完成，可以从上传 GitHub 的第 3 步继续。

**购买域名后，按部署文档第 7 步将网站文件里的 `https://example.com` 替换成真实主地址，再提交站点地图。**

## 文件

- `public/index.html`：英文首页。
- `public/zh/index.html`：简体中文工具页。
- `public/assets/app.js`：两种语言共用的生成、校验及复制逻辑。
- `public/assets/styles.css`：电脑和手机共用的样式。
- `public/sitemap.xml`、`public/robots.txt`：搜索准备文件。
- `tests/check_site.py`：可选的浏览器自动检查工具；不参与网站部署。

## 开发者检查

网站本身不依赖 Python 或 Playwright。可选测试需要 Python 和 Playwright 的 Chromium 浏览器，环境准备好后执行：

```powershell
python -m pip install playwright
python -m playwright install chromium
python tests/check_site.py
```

测试自动启动临时本地服务并检查两种语言、输入限制、v4 格式、复制成功与失败、异常生成器、键盘操作和窄屏显示。复制测试用可控的浏览器接口模拟允许和拒绝复制，避免改动电脑剪贴板。截图写入已忽略的 `.test-artifacts/`。

检查结果及上线进度见《03-实现与检查记录.md》。
