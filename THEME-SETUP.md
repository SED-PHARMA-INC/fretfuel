# FretFuel Shopify 主题

这是根据 `FretFuel-standalone-compatible.html` 重建的 Shopify Online Store 2.0 主题。视觉资源从原 HTML 提取，页面使用 Liquid、JSON 模板和 Shopify 主题资源；商品、价格、库存、搜索、购物车和结账使用店铺真实数据。

## 使用

1. GitHub 同步方式：将本目录的 `assets`、`config`、`layout`、`locales`、`sections`、`snippets`、`templates` 放在仓库根目录。在 Shopify 后台的“在线商店 → 模板”中选择“从 GitHub 连接”，授权 Shopify GitHub 应用，选择仓库和 `main` 分支。先保留为未发布主题并预览。
2. 也可以将本地的 `fretfuel-shopify.zip` 作为主题上传到 Shopify，或用 Shopify CLI 推送到开发店铺。GitHub 连接与 ZIP 上传二选一即可。
3. 在店铺中添加真实商品、图片、变体和价格。若要展示可旋转的 3D 商品，在 Shopify 商品后台的媒体区上传 3D 模型，并确认媒体处理完成。商品页会显示带“3D”标记的缩略图；顾客选择后点击“View 3D model”即可旋转查看。单独上传封面图片不会产生 3D 模型。首页默认读取“所有商品”；可以在主题编辑器中为精选商品和组件区域指定集合。
4. 首页九个零件分类优先打开主题编辑器中选择的商品集合。未配置或找不到集合时，按该分类的商品类型筛选，不再回退到“所有商品”。可在分类块的“Product type if no collection”中填写店铺实际使用的商品类型；留空时按默认分类图片使用下表类型，因此只修改显示标题或翻译不会改变分类。没有匹配商品时显示该分类的空结果页。
5. 在页眉设置中可选一个 Shopify 导航菜单。默认导航优先打开对应商品集合，找不到集合时按商品类型筛选。大分类匹配多个相关类型，例如“Bridges & tailpieces”包含 `Bridge`、`Tremolo bridges` 和 `Tailpieces`。子分类按自己的类型筛选，例如“颤音琴桥”只匹配 `Tremolo bridges`。菜单底部的“Browse all parts”打开全部商品。
6. 如需独立选购指南，可创建一个页面并指定 `page.parts-guide` 模板，再将该页面设为页眉、页脚和首页的指南链接。不指定时，链接会跳到首页的指南区块。
7. 如果需要集合筛选，在 Shopify 中为商品配置筛选条件。主题会展示集合可用的前四个列表筛选项和排序控件。

## 可选商品字段

商品卡片和详情页会读取以下可选 metafield：

| Namespace / key | 用途 |
| --- | --- |
| `custom.series` | 系列标签 |
| `custom.finish` | 表面处理 |
| `custom.key_dimension` | 关键尺寸 |

这些字段为空时，页面仍可使用。

## 原型与正式商品

原 HTML 内的九个商品、价格、规格和浏览器本地购物袋属于设计预览。主题没有将它们导入为可购买商品，也没有使用原型价格。提取的图片素材仍适合做版式展示；正式销售前应配置每款商品的实拍图、测量数据和实际售价。

## 验证

在主题目录运行 `shopify theme check`。要验证真实商品表单、支付和店铺配置，还需要在 Shopify 开发店铺中预览。

## 首页零件分类配置

在 Shopify 后台“产品”的商品组织信息中填写“类型（Type）”，使用以下类型值；也可以创建专门的商品集合，再到主题编辑器的首页分类块中选择该集合。产品所属的 Hero / Stage / BLACK / BLACK X 系列与零件类型是不同的分类维度。

| 首页分类 | 默认商品类型 | 预设集合 handle |
| --- | --- | --- |
| 吉他调音器 | `Guitar tuners` | `guitar-tuners` |
| 贝斯调音器 | `Bass tuners` | `bass-tuners` |
| 颤音琴桥 | `Tremolo bridges` | `tremolo-bridges` |
| 尾件 | `Tailpieces` | `tailpieces` |
| 拾音器 | `Pickups` | `pickups` |
| 电子元件 | `Electronics` | `electronics` |
| 护板 | `Pickguards` | `pickguards` |
| 琴码 | `Saddles` | `saddles` |
| 旋钮 | `Knobs` | `knobs` |

已有主题中的分类块会保留原来选中的集合；如果“吉他调音器”原来选的是同时包含吉他与贝斯调音器的 `tuners` 集合，或“颤音琴桥”原来选的是包含其他琴桥的 `bridges` 集合，应改选上表的专用集合，或清空集合选择后使用商品类型筛选。

未填写类型且未加入所选集合的商品不会出现在相应分类中。合并主题修复后，还需完成商品归类才能让分类页显示商品；主题更新不会自动修改商品数据。分类入口使用 Shopify 的[字段搜索语法](https://help.shopify.com/en/manual/online-store/storefront-search/search-behavior#search-syntax)，只查询匹配的商品类型，空分类也可以正常打开。
