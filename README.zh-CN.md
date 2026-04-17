# seo-inspection

[English README](README.md)

`seo-inspection` 是一个可复用的 SEO 证据 skill，用 Google Search Console 和 GA4 API 支撑索引、抓取、robots、sitemap、Search Analytics、产品页流量、engagement、conversion、revenue 和 SEO/GEO 优先级判断。

## 能力范围

- GSC URL Inspection、Search Analytics、Sites、Sitemaps。
- GA4 Admin property discovery 和 Data API 报告。
- 产品页 GA4 数据按 Shopify handle 聚合。
- GA4 landing pages、channels、geo、devices、events、ecommerce items、timeseries 预设报告。
- GA4 batch report、pivot report、compatibility check、realtime report。
- GSC 写操作默认 dry-run，必须显式加 `--apply`。

## 安装

在 skill 目录执行：

```powershell
python -m pip install -r requirements.txt
```

## 配置

配置读取顺序：

1. skill 目录 `.env`
2. 项目根目录 `.env`
3. 环境变量覆盖文件配置

复制 `.env.example` 为 `.env`：

```env
GSC_SERVICE_ACCOUNT_PATH=credential/google-service-account.json
GOOGLE_SERVICE_ACCOUNT_PATH=credential/google-service-account.json
GSC_SITE_URL=sc-domain:example.com
GSC_LANGUAGE_CODE=en-US
GA4_PROPERTY_ID=123456789
```

注意：

- `GA4_PROPERTY_ID` 是数字 property ID，不是 `G-...` measurement ID。
- 可以用同一个 service account 同时访问 GSC 和 GA4。
- 不要提交真实 `.env`、service account JSON、`temp/` 输出或 `__pycache__/`。

## Google 权限

1. 创建或复用 Google service account。
2. 将 service account email 加到 Search Console property。
3. 将同一个 service account email 加到 GA4 property，并授予只读权限。
4. 在 `.env` 填好 JSON 路径、GSC property 和 GA4 property ID。
5. 用 `ga4-account-summaries` 验证 GA4 权限。

## 常用命令

GSC：

```powershell
python scripts/seo_inspection.py sites-list --output temp/gsc-sites.json
python scripts/seo_inspection.py sitemaps-list --output temp/gsc-sitemaps.json
python scripts/seo_inspection.py inspect --url "https://example.com/products/example" --output temp/url-inspection.json
python scripts/seo_inspection.py searchanalytics-query --start-date 2026-01-01 --end-date 2026-01-31 --dimensions query,page --output temp/gsc-searchanalytics.json
```

GSC 写操作：

```powershell
python scripts/seo_inspection.py sitemaps-submit --sitemap-url "https://example.com/sitemap.xml"
python scripts/seo_inspection.py sitemaps-submit --sitemap-url "https://example.com/sitemap.xml" --apply
```

GA4 discovery：

```powershell
python scripts/seo_inspection.py ga4-account-summaries --output temp/ga4-account-summaries.json
python scripts/seo_inspection.py ga4-metadata --output temp/ga4-metadata.json
python scripts/seo_inspection.py ga4-check-compatibility --dimensions pagePath --metrics sessions,totalRevenue --output temp/ga4-compatibility.json
```

GA4 presets：

```powershell
python scripts/seo_inspection.py ga4-product-pages --start-date 2026-01-17 --end-date 2026-04-16 --aggregate-by-handle --output temp/ga4-product-pages.json
python scripts/seo_inspection.py ga4-landing-pages --start-date 2026-01-17 --end-date 2026-04-16 --output temp/ga4-landing-pages.json
python scripts/seo_inspection.py ga4-channels --start-date 2026-01-17 --end-date 2026-04-16 --output temp/ga4-channels.json
python scripts/seo_inspection.py ga4-geo --start-date 2026-01-17 --end-date 2026-04-16 --dimension country --output temp/ga4-countries.json
python scripts/seo_inspection.py ga4-devices --start-date 2026-01-17 --end-date 2026-04-16 --dimension deviceCategory --output temp/ga4-devices.json
python scripts/seo_inspection.py ga4-events --start-date 2026-01-17 --end-date 2026-04-16 --output temp/ga4-events.json
python scripts/seo_inspection.py ga4-ecommerce-items --start-date 2026-01-17 --end-date 2026-04-16 --output temp/ga4-items.json
python scripts/seo_inspection.py ga4-timeseries --start-date 2026-01-17 --end-date 2026-04-16 --output temp/ga4-timeseries.json
```

GA4 advanced：

```powershell
python scripts/seo_inspection.py ga4-report --start-date 2026-01-17 --end-date 2026-04-16 --dimensions pagePath --metrics sessions,engagementRate,conversions,totalRevenue --output temp/ga4-custom.json
python scripts/seo_inspection.py ga4-batch-report --requests-file temp/ga4-batch-requests.json --output temp/ga4-batch.json
python scripts/seo_inspection.py ga4-pivot-report --body-file temp/ga4-pivot-body.json --output temp/ga4-pivot.json
python scripts/seo_inspection.py ga4-realtime-report --dimensions unifiedScreenName --metrics activeUsers --output temp/ga4-realtime.json
```

复杂 GA4 示例见 `references/ga4-recipes.md`。

## 推荐判断口径

- GSC 回答 Google 搜索需求、query 语言、索引、抓取、robots、sitemap。
- GA4 回答落地后的 session、engagement、conversion、revenue、channel、device、country。
- 做 metadata、产品页 SEO、GEO/AEO 和内容优先级时，优先结合 GSC + GA4。

## 验证

```powershell
python -m py_compile scripts/seo_inspection.py
python scripts/seo_inspection.py sites-list --output temp/gsc-test.json
python scripts/seo_inspection.py ga4-account-summaries --output temp/ga4-test.json
python scripts/seo_inspection.py ga4-product-pages --start-date 2026-04-01 --end-date 2026-04-16 --limit 2 --aggregate-by-handle --output temp/ga4-product-test.json
```

## 发布前检查

- `SKILL.md` frontmatter 有效，`name: seo-inspection`。
- `scripts/seo_inspection.py` 能编译，至少一个 GSC 和一个 GA4 命令跑通。
- `.env.example` 不含真实凭据。
- `.gitignore` 排除 `.env`、`credential/`、`temp/`、`outputs/`、`__pycache__/`。
- README 和 `references/ga4-recipes.md` 覆盖安装、配置、调用、验证。
