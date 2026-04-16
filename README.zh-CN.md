# gsc-inspection

[English README](README.md)

`gsc-inspection` 是一个可复用的 Google Search Console API skill，用于用 API 证据排查索引、抓取、`robots.txt`、站点属性、sitemap 和 Search Analytics 问题。

它适合在修改 canonical、hreflang、sitemap、内部链接或 robots 规则之前，先用 Search Console 的实际数据确认问题是否仍然存在。

## 包含内容

- `SKILL.md`：给 AI agent 使用的触发说明和工作流
- `scripts/gsc_inspection.py`：Search Console API CLI 工具
- `.env.example`：配置模板
- `samples/`：脱敏输入和输出示例

## 配置方式

工具会读取两个位置的配置：

1. skill 目录下的 `.env`
2. 项目根目录的 `.env`

如果两个文件都存在，skill 目录下的 `.env` 优先。

必填配置：

```env
GSC_SERVICE_ACCOUNT_PATH=credential/google-service-account.json
GSC_SITE_URL=sc-domain:example.com
```

可选配置：

```env
GSC_LANGUAGE_CODE=en-US
```

只提交 `.env.example`，不要提交真实 `.env`。

## 凭据设置

1. 创建 Google service account。
2. 下载 service account JSON。
3. 将 JSON 放在你自己的项目中，例如：

```text
credential/google-service-account.json
```

4. 在 Search Console 中，把 service account email 添加到目标属性，并授予足够权限。
5. 在 `.env` 中配置 `GSC_SERVICE_ACCOUNT_PATH` 和 `GSC_SITE_URL`。

## 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## API 覆盖范围

当前 CLI 覆盖 Google Search Console 公开 API 的主要能力：

- `sites-list`
- `sites-get`
- `sites-add`
- `sites-delete`
- `sitemaps-list`
- `sitemaps-get`
- `sitemaps-submit`
- `sitemaps-delete`
- `searchanalytics-query`
- `inspect`

写操作需要显式加 `--apply`。没有 `--apply` 时，命令只返回 dry-run 结果，不会执行写入。

官方参考：

- Search Console API reference: https://developers.google.com/webmaster-tools/v1/api_reference_index
- URL Inspection API: https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect
- Search Analytics query: https://developers.google.com/webmaster-tools/v1/searchanalytics/query

## 常用命令

检查单个 URL：

```powershell
python scripts/gsc_inspection.py inspect `
  --url "https://example.com/missing-page" `
  --output temp/gsc-inspection-run.json
```

批量检查 URL：

```powershell
python scripts/gsc_inspection.py inspect `
  --input-file temp/gsc-urls.txt `
  --output temp/gsc-inspection-run.json
```

列出 Search Console 属性：

```powershell
python scripts/gsc_inspection.py sites-list `
  --output temp/gsc-sites.json
```

列出已提交 sitemap：

```powershell
python scripts/gsc_inspection.py sitemaps-list `
  --output temp/gsc-sitemaps.json
```

获取单个 sitemap：

```powershell
python scripts/gsc_inspection.py sitemaps-get `
  --sitemap-url "https://example.com/sitemap.xml" `
  --output temp/gsc-sitemap.json
```

提交 sitemap：

```powershell
python scripts/gsc_inspection.py sitemaps-submit `
  --sitemap-url "https://example.com/sitemap.xml" `
  --apply `
  --output temp/gsc-sitemap-submit.json
```

查询 Search Analytics：

```powershell
python scripts/gsc_inspection.py searchanalytics-query `
  --start-date 2026-01-01 `
  --end-date 2026-01-31 `
  --dimensions query,page `
  --row-limit 1000 `
  --output temp/gsc-searchanalytics.json
```

按页面过滤 Search Analytics：

```powershell
python scripts/gsc_inspection.py searchanalytics-query `
  --start-date 2026-01-01 `
  --end-date 2026-01-31 `
  --dimensions query,page `
  --dimension-filter-groups '[{"filters":[{"dimension":"page","operator":"contains","expression":"/products/"}]}]' `
  --output temp/gsc-searchanalytics-products.json
```

## 示例文件

这些文件是脱敏示例，使用 `example.com`：

```text
samples/urls.txt
samples/inspection-output.example.json
samples/searchanalytics-output.example.json
samples/sitemaps-output.example.json
```

运行脚本前，请替换成你自己 Search Console 属性下的 URL。

## 常见用途

- 判断 GSC 的 `Not found (404)` 是历史遗留还是当前仍然被站点输出。
- 验证 `Blocked by robots.txt` 是否属于预期拦截。
- 在修改 canonical、hreflang、robots 或 sitemap 之前，先查看 `referringUrls`。
- 区分内部平台生成 URL 和真正的前台页面问题。
- 批量导出证据文件，用于 SEO 清理。
- 验证重定向、canonical 或 hreflang 修复是否被 Google 重新识别。
- 查询 Search Analytics 中 query、page、country、device、date 等维度表现。
- 查看 Search Console 属性和 sitemap 提交状态。

## 实战流程

### 迁移后的 404 清理

1. 从 GSC 导出代表性 URL。
2. 每行一个 URL 放入输入文件。
3. 运行 `inspect --input-file`。
4. 按 `classification` 分组。
5. 对有 `referringUrls` 的 URL，先抓取 referring page 再决定是否加 redirect。
6. 对没有 live source、且抓取时间较旧的 URL，通常按历史遗留处理。

### robots block 排查

1. 使用 `inspect` 检查 URL。
2. 确认 `robotsTxtState` 是否为 `DISALLOWED`。
3. 对照 robots 规则确认是否为预期拦截。
4. 只有当该 URL 应该被索引时，才修改 robots 规则。

### 参数 URL 排查

适用于 tracking、sort、filter、search、recommendation、session 参数。

1. 检查完整参数 URL。
2. 查看 Google 是否返回 `referringUrls`。
3. 判断该 URL 应该 canonicalize、redirect、block、noindex，还是保持现状。
4. 不要在没有证据时大范围封禁参数 URL。

### canonical mismatch 排查

1. 检查 GSC 报告 URL 和目标 canonical URL。
2. 抓取 live HTML，确认 `<link rel="canonical">`。
3. 检查内部链接是否仍指向重复 URL。
4. 只有 live evidence 仍错误时才改模板。

### hreflang 和本地化 URL 验证

1. 检查错误本地化 URL 和预期本地化 URL。
2. 查找重复语言前缀或混合 locale 路径。
3. 检查 referring URL 和 live alternate links。
4. 如果当前页面不再输出错误路径，通常按历史遗留处理。

### sitemap 验证

1. 检查 URL。
2. 查看是否有 `referringUrls`。
3. 单独抓取 sitemap 或 sitemap index。
4. 如果 sitemap 已不再列出该 URL，重复抓取通常是 stale discovery。

## 输出说明

脚本输出 JSON，包含：

- Search Console 属性访问结果
- 每个 URL 的 Inspection 结果
- 标准化摘要字段
- 自动分类和分类理由

主要分类：

- `historical_malformed_domain_repeat_404`
- `historical_malformed_multilang_404`
- `shopify_internal_robots_block`
- `robots_blocked_other`
- `not_found_with_referring_source`
- `not_found_without_referrer`
- `needs_manual_review`

## 发布注意事项

这个 skill 是通用设计：

- `SKILL.md` 不写死具体站点
- 私有配置放在 `.env`
- 示例文件只使用 `example.com`

发布前检查：

1. 不提交 `.env`
2. 不提交 `credential/`
3. 不提交真实 GSC 输出
4. 不提交 service account JSON
5. 确认样例中没有客户域名、token 或私钥

## 当前限制

- 工具覆盖 Search Console 公开 API，但不是每个 GSC UI 报表都有 API。
- 自动分类是启发式，用于 triage，不替代 live source 检查。
- 工具当前不会自动抓取 live HTML；有 referring source 时仍建议单独抓页面验证。

## 后续可增强

- 自动抓取 referring URL 并验证是否还输出坏链接。
- CSV 输入和 CSV 摘要输出。
- sitemap URL membership 检查。
- 将 JSON 输出自动生成 Markdown 报告。
