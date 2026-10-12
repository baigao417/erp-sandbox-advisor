# 输入约定 v1

以 `data/examples/synthetic_scenario.json` 作为完整模板。每层对象只接受模板中列出的字段；不默默忽略未知键。CLI 拒绝重复 JSON 键。数值必须有限；金额及权重非负，建议写为字符串。数量、阈值和期次必须是非负 JSON 整数，布尔值不算整数。订单数量必须大于零。

| 区域 | 字段及语义 |
| --- | --- |
| 根对象 | `schema_version` 固定为整数 `1`；其余为下列区域 |
| `company` | `opening_cash` 期初现金、`equity` 用于排名的权益；`markets`、`products`、`certifications` 为已取得资格的标识列表 |
| `cash_events[]` | `label` 事件标识、`inflow` 收入、`outflow` 支出；按数组顺序计算余额 |
| `inventory` | 产品标识映射到库存数量，仅代表一次快照 |
| `orders[]` | `id` 唯一标识；`market`、`product` 对应公司资格；`quantity`、`unit_price`、`unit_cost`、`allocated_cost` 用于贡献计算 |
| 订单资格 | `required_certifications` 必须是公司资格的子集；`ready_period <= delivery_period`；`available_units >= quantity` |
| `ranking` | `advertising` 广告金额；`equity_weight`、`advertising_weight` 非负且合计为一 |
| `inventory_rules` | `per_product_limit`、`total_limit` 为免罚阈值；`penalty_per_unit` 为每单位罚款；`overlap` 为 `max` 或 `add` |
| `annual_bands[]` | `above` 为严格超过的库存阈值，按严格递增顺序填写；`fee` 为该档总费用。取最后一个满足条件的档位，不叠加 |

市场、产品、认证、订单 ID 和事件标签均是区分大小写的非空字符串；不要填写个人身份或保密内容。订单必须包含全部字段，即使无需认证也要填写空列表。空订单、现金事件、库存和年度费用档位均可接受。

## 输出语义

- `cash.minimum_cash` 包括期初余额及每个事件的期末余额；`funding_gap` 是负余额的最大绝对值。事件内收支先净额结算，无法看见事件内部的付款顺序。
- `ranking_score = equity × equity_weight + advertising × advertising_weight`，并非排名名次。
- `per_product_excess` 是各产品超限数量之和；`total_excess` 是总量超限部分。`charged_units` 根据 `overlap` 选择较大值或求和。
- `contribution = quantity × (unit_price - unit_cost) - allocated_cost`；`profitable` 表示贡献严格大于零。
- 订单先按资格通过排序，再按贡献降序，最后按 ID 排序；这不是组合优化，不能直接把排列当成接单建议。
- 所有金额输出为十进制字符串，避免 JSON 二进制浮点误差。字段错误时 CLI 只给通用错误提示，不回显输入内容。

人工将适用规则转为配置后，先以独立手算样例核对，再用于教学方案比较。工具不会从教材、网络或模型补全未知规则。
