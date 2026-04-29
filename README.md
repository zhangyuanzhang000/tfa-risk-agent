# 🌱 TFA Risk Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-green.svg)](https://openclaw.ai)

> **TFA（热带森林联盟）可持续供应链风险评估专业Agent v3.2**

TFA Risk Agent 是一款专注于六大软性商品可持续供应链风险评估的专业Agent，严格遵循热带森林联盟（TFA）尽调手册，全面契合 EUDR（欧盟无毁林产品法规）、CSRD（企业可持续发展报告指令）、CDP（碳信息披露项目）、AFi（森林信息披露倡议）、OECD（经合组织）等多项国际核心标准，为棕榈油、大豆、牛肉、咖啡、可可、橡胶六大软性商品的供应链风险提供精准评估。
核心目标是实现可持续供应链风险评估全流程自动化，通过交互化沟通，将复杂的评估工具转化为高效可操作的自动化流程，覆盖 报告上传→证据抽取→人工审核→风险评级→评估报告全自动生成 全环节。区别于传统线性流程Agent，本品采用“人在环”模式，会在评估范围确认、信息补充、风险评估凭证审核等多个关键节点与用户深度交互沟通，过程留存完整证据链，人工审核环节确保结果严谨，支持后续审计与复盘，既实现流程自动化高效运转，又通过人机协同确保评估精准度与贴合度。

---

## ✨ 核心特性

### 🔬 双指标评估体系

| 指标 | 方法 | 用途 |
|------|------|------|
| **Overall Risk Score** | MAX(7维度) | 触发强制性增强尽职调查(EDD) |
| **Weighted Risk Index (WRI)** | Σ(得分×权重) | 风险比较与优先级排序 |

### 📊 7维度风险评估

- 🌲 **毁林风险** (30%) - Global Forest Watch, TRASE
- 🌡️ **气候脆弱性** (30%) - ND-GAIN Index  
- 🇪🇺 **EUDR暴露** (20%) - 欧盟官方高风险地区清单
- 📦 **生产体量** (15%) - FAOSTAT
- 🔍 **溯源风险** (15%) - 企业DDQ回答评估
- 👷 **劳工/社会风险** (10%) - 美国劳工部童工清单
- 🏞️ **保护区影响** (5%) - 联合国保护区数据库

### 🎯 支持商品

| 商品 | 状态 | 专属DDQ |
|------|------|---------|
| 棕榈油 | ✅ | 10道专属问题 |
| 大豆 | ✅ | 14道专属问题 |
| 牛 | ✅ | 7道专属问题 |
| 咖啡 | ✅ | 5道专属问题 |
| 可可 | ✅ | 7道专属问题 |
| 橡胶 | ✅ | 6道专属问题 |

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/zhangyuanzhang000/tfa-risk-agent.git
cd tfa-risk-agent

# 安装依赖
pip install -r requirements.txt
```

### 使用方法

#### 方式1：作为 OpenClaw Skill 使用

在 OpenClaw 中激活：
```
TFA 风险评估
```

#### 方式2：命令行使用

```bash
# 生成完整评估报告
python report_generator_v3.2.py \
  --input "DDQ评估表.csv" \
  --output "./output" \
  --company "企业名称"
```

#### 方式3：完整评估流程

```bash
python run_full_assessment.py --config assessment_config.json
```

---

## 📁 项目结构

```
tfa-risk-agent/
├── SKILL.md                      # Skill 定义文件（核心）
├── config.json                   # Skill 配置文件
├── README.md                     # 本文件
├── requirements.txt              # Python 依赖
├── report_generator_v3.2.py      # 主报告生成器（推荐）
├── run_full_assessment.py        # 完整评估流程
├── generate_anta_report.py       # 安踏报告生成示例
├── assets/
│   └── ddq_template.csv          # DDQ评估表模板
├── references/                   # 参考文档
│   ├── ddq-questions.md          # DDQ题库
│   ├── eudr-compliance.md        # EUDR合规指南
│   ├── csrd-requirements.md      # CSRD要求
│   ├── cdp-forest.md             # CDP森林问卷
│   ├── afi-framework.md          # AFi框架
│   ├── oecd-guidelines.md        # OECD指南
│   ├── palm-oil-standards.md     # 棕榈油标准
│   └── soy-standards.md          # 大豆标准
├── scripts/                      # 工具脚本
│   ├── extract_evidence.py       # 证据提取
│   ├── feedback_collector.py     # 反馈收集
│   ├── feedback_analyzer.py      # 反馈分析
│   └── continuous_improvement.py # 持续优化
├── feedback/                     # 反馈系统
│   ├── README.md
│   ├── USAGE.md
│   └── schema.json
├── learning/                     # 学习记录
│   └── corrections.json
└── output/                       # 输出目录（示例）
```

---

## 📋 工作流程

```
用户触发: "TFA 风险评估"
    ↓
[第一阶段] 启动与评估前置
    - 双路径分流（知识问答/正式评估）
    - 信息采集 → 报告解析 → 范围确认
    ↓
[第二阶段] DDQ问题扫描与证据抓取
    - 加载DDQ题库 → 全文检索 → 逐题匹配
    - 生成评估表 → 人工审核
    ↓
[第三阶段] 风险综合评估与HTML报告生成
    - Regional Risk Matrix分析
    - Overall Risk Score + WRI计算
    - 风险暴露与管理匹配分析
    - 交互式HTML报告生成
    ↓
交付物:
    ├── DDQ尽调评估表 (CSV)
    ├── TFA风险评估报告 (HTML)
    ├── 数据缺口清单 (CSV)
    └── 证据索引 (CSV)
```

---

## 📦 交付物说明

### 1. DDQ尽调评估表 (CSV)

包含完整证据链的评估表：
- DDQ编号与问题原文
- 证据原文与来源
- 证据等级 (Tier1/Tier2/Tier3)
- 人工审核状态与备注

### 2. TFA风险评估报告 (HTML)

交互式可视化报告，包含9个章节：
1. Header - 企业信息与评估期间
2. 核心指标卡片 - Overall Score, WRI, 管理能力, DDQ完整度
3. Regional Risk Matrix - 7维度完整表格
4. 风险暴露与管理匹配分析
5. 两栏图表 - WRI对比 + 7维度热力图
6. 风险管理能力评估 - 5维度柱状图
7. 关键发现 - 带图标的5-6条核心发现
8. 优先行动建议 - 按优先级排序
9. 数据缺口清单 - 缺口编号、描述、优先级

### 3. 数据缺口清单 (CSV)

基于审核结果识别的所有数据缺口：
- 缺口编号、对应DDQ
- 缺口描述、数据要求
- 法规依据、优先级

---

## 🔄 持续优化系统 (v3.3)

TFA Risk Agent 内置**闭环反馈学习系统**：

### 三层反馈机制

1. **即时反馈** - DDQ评估表中每题的反馈
2. **评估反馈** - 评估完成后的整体满意度
3. **长期优化** - 每周分析并生成优化建议

### 使用方法

```bash
# 收集反馈
python scripts/feedback_collector.py \
  --type instant \
  --assessment-id asm_xxx \
  --data '{...}'

# 分析反馈
python scripts/feedback_analyzer.py \
  --period 7d \
  --output report.md

# 生成优化任务
python scripts/continuous_improvement.py \
  --period 7d \
  --generate-tasks
```

---

## 🛠️ 开发

### 本地开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
python -m pytest tests/

# 代码格式化
black .
isort .
```

### 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📚 文档

- [SKILL.md](SKILL.md) - 完整的Skill使用文档
- [references/](references/) - 法规与标准参考
- [feedback/USAGE.md](feedback/USAGE.md) - 反馈系统使用指南

---

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证。

---

## 🙏 致谢

- [热带森林联盟 (TFA)](https://www.tropicalforestalliance.org/) - 尽调手册与框架
- [Global Forest Watch](https://www.globalforestwatch.org/) - 毁林数据
- [TRASE](https://trase.earth/) - 供应链透明度数据

---

## 📞 联系

如有问题或建议，欢迎通过以下方式联系：
- 提交 [Issue](https://github.com/zhangyuanzhang000/tfa-risk-agent/issues)
- 发送邮件到 zhangyuanzhang000@example.com

---

**版本**: v3.2.0 | **更新日期**: 2026-04-28
