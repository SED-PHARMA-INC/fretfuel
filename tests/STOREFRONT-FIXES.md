# 分类、空系列、指南与窄屏修复验证

日期：2026-11-24。分支：`fix/storefront-navigation-guides-20261124`；基线：`3654df5`。

## 结果

- 自动化测试 39 项通过，其中新增 11 项，覆盖原始及 HTML 编码的分类查询、三个汇总大类、浏览器标题、页眉搜索框、特殊字符与注入文本、分类分页、空系列返回、指南默认链接、自定义链接和语言路径。
- 原有普通搜索 DOM 回归、分类映射及 400 组转义随机输入继续通过。首页回归比较仅排除本次有意修改的分类和指南区块，并归一化指南默认锚点，继续比较其余区域。
- Shopify Theme Check 检查 32 个文件，无问题；JavaScript 语法及 `git diff --check` 通过。
- Edge 本地实测：Pickups 及三个汇总大类显示对应标题，页眉搜索框为空，正文不显示内部查询；普通关键词搜索仍显示搜索表单。
- Edge 本地实测：空 Hero 集合的“View all parts”进入全部商品；三个指南入口打开各自内容；刷新指南深链接会展开该主题，关闭后点击同一锚点可以重新展开。
- Edge 实际 CSS 视口为 320、360、400、768 像素时，文档 `scrollWidth` 均等于 `clientWidth`，没有横向溢出。测试浏览器缩放为 75%，按实际 CSS 视口校准测试尺寸，测试后恢复视口覆盖设置。
- 浏览器测试未记录 JavaScript 错误。

## 复跑

```powershell
python -m unittest discover -s tests -v
node --check assets/fretfuel-theme.js
shopify theme check
git diff --check
python tests/category_harness.py --serve 8767
```

Python 环境需安装 `tests/requirements.txt`。本地页面使用仓库中的真实布局、页眉、页脚、区块、片段、CSS 与 JavaScript；`/collections/hero` 等系列集合使用空的合成数据，以便检查返回按钮；`/pages/parts-guide` 用于验证独立指南模板。

## 验证边界

本地适配器模拟 Shopify 的搜索结果、HTML 编码的 `search.terms` 与分页，不能替代 Shopify 平台的真实搜索集成。没有将未合并主题上传或发布到 Shopify，没有修改商品、政策、支付设置，也没有提交订单。用户合并并同步主题后，应在真实店铺补验分类标题、分类分页、空系列返回及指南跳转。
