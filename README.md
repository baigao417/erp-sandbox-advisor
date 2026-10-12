# ERP Sandbox Advisor

An offline, dependency-free Python CLI for configurable ERP simulation checks: cash exposure, order eligibility and contribution, ranking scores, and inventory charges. All included scenarios are fictional.

ERP 企业模拟经营沙盘的轻量决策辅助器。将现金、订单资格和库存规则结构化，减少只看销售额、遗漏收款时点或资格限制的问题。作者：`baigao417`。

当前公开版是**最小计算原型**，不是完整经营仿真平台，也不是自动决策 Agent。包含的输入、数值、产品与市场标识全部为合成数据，不对应任何真实对局。

## 核心机制

```text
JSON 场景（资格、订单、现金事件、规则参数）
    -> 严格字段及数值校验
    -> Decimal 纯计算核心
       |-- 按事件顺序检查现金余额及最大缺口
       |-- 逐单检查资格、交期和可用数量，计算贡献
       |-- 按配置权重计算排名分值
       `-- 按库存快照计算超额罚款和年度费用
    -> JSON 结果（风险、阻塞项、计算假设）
    -> 人工核对规则与方案
```

没有网络访问、模型调用、数据库或自动文件写入。CLI 只读取指定 JSON 并向标准输出打印结果。

## 快速开始

需要 Python 3.10 或更高版本。无第三方依赖，无需安装包。以下命令在仓库根目录执行。

PowerShell：

```powershell
$env:PYTHONPATH = "src"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -m erp_sandbox_advisor --help
python -B -m erp_sandbox_advisor data/examples/synthetic_scenario.json
python -B -m unittest discover -s tests -v
```

Linux / macOS：

```bash
PYTHONPATH=src python -B -m erp_sandbox_advisor data/examples/synthetic_scenario.json
PYTHONPATH=src python -B -m unittest discover -s tests -v
```

合成示例的期末现金为 `30`，最低现金为 `18`；排名分值为 `34.0`；库存期间罚款为 `2`，年度费用为 `1`。`order_alpha` 贡献为 `13` 且通过资格检查；`order_beta` 因资格、交期和数量不足被标记。

退出码：有效分析为 `0`；输入无效或无法读取为 `2`。现金缺口或订单受阻属于有效分析结果，调用者应检查 JSON 内的 `cash.safe`、`eligible` 和 `blockers`，不能仅依赖退出码。

## 配置说明

唯一业务配置入口是场景 JSON，详见 [输入约定](docs/input-contract.md) 与 [合成模板](data/examples/synthetic_scenario.json)。无需 `.env`、API key 或 provider 配置。

- 金额建议使用十进制字符串；单位由调用者统一，不混用单位。
- 所有字段均必填；未知字段、重复 JSON 键和重复订单 ID 会被拒绝。
- 规则权重必须非负且合计为 `1`。库存阈值、罚款单价、年度费用档位均可配置。
- 同时触发单品和总库存阈值时，`overlap=max` 取两种超额数量的较大者，`add` 累加；应由适用规则决定，示例不是权威规则。
- 现金事件必须按实际发生顺序录入。要捕捉先付后收的缺口，应拆成两个事件。
- 通用分析方法见 [规则摘要](docs/rule-summary.md)，可人工使用的提示词见 [决策核对](prompts/decision-review.md)。

## 已知限制

- 不计算完整利润表、资产负债表或多年经营状态，不执行生产排程、采购倒排、贷款贴现、研发进度、广告选单数量或策略搜索。
- 每个订单独立评估，不扣减其他订单占用的产能或库存；通过检查不意味着订单组合可交付。
- `ready_period` 与 `available_units` 是用户声明，不是工具推导或验证的生产能力；不校验材料提前期和生产线冲突。
- 订单贡献仅为收入减直接成本与分摊费用，不是净利润。非盈利订单仍可能具备资格，结果会分别标记。
- 订单、库存罚款和年度费用不会自动进入现金流。调用者必须完整录入相关付款与回款；现金安全仅对这些事件成立。
- 排名只输出单个分值，没有竞争对手数据，不预测获单概率。库存计算只针对单个快照，不自动判断年度或季度适用性。
- JSON 不包含个人身份字段，但仍可自由填写字符串；处理真实数据前需自行匿名化，不应提交真实盘面或结果。

## 免责声明

本项目仅用于学习、建模与方案核对，不构成经营、财务或比赛获胜保证。比赛或课程规则需由使用者取得授权并自行确认，任何示例参数均不可视为官方规则。最终方案、数据合法性与风险接受由使用者负责。

## 许可

项目自写代码与文档采用 MIT，见 [LICENSE](LICENSE)。不包含课程原件、第三方文章、素材或 vendored 代码；本许可不授予对外部教材、平台内容或比赛资料的使用权，见 [第三方说明](THIRD_PARTY_NOTICES.md)。
