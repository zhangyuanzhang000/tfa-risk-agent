#!/usr/bin/env python3
"""
TFA Risk Agent 定期优化脚本

功能：
1. 定期分析反馈数据
2. 识别高频错误模式
3. 生成优化建议报告
4. 更新学习记录
5. 触发必要的规则更新

用法：
    # 手动运行（分析最近7天）
    python3 continuous_improvement.py --period 7d
    
    # 自动模式（由cron调用）
    python3 continuous_improvement.py --auto
    
    # 生成优化任务清单
    python3 continuous_improvement.py --generate-tasks
"""

import json
import os
import sys
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# 路径设置
SKILL_DIR = Path(__file__).parent.parent
FEEDBACK_DIR = SKILL_DIR / "feedback"
LEARNING_DIR = SKILL_DIR / "learning"
IMPROVEMENTS_DIR = FEEDBACK_DIR / "improvements"


def run_feedback_analysis(period_days: int = 7) -> dict:
    """运行反馈分析"""
    print(f"🔍 分析最近 {period_days} 天的反馈数据...")
    
    analyzer_script = SKILL_DIR / "scripts" / "feedback_analyzer.py"
    
    # 运行分析器
    result = subprocess.run(
        [sys.executable, str(analyzer_script), "--period", f"{period_days}d", "--save-analysis"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ 分析失败: {result.stderr}")
        return None
    
    print(result.stdout)
    
    # 读取最新的分析结果
    pattern_files = sorted((FEEDBACK_DIR / "patterns").glob("patterns_*.json"))
    if pattern_files:
        latest_file = pattern_files[-1]
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return None


def generate_improvement_report(analysis_data: dict) -> str:
    """生成优化报告"""
    report_date = datetime.now().strftime("%Y%m%d")
    report_path = IMPROVEMENTS_DIR / f"improvement_report_{report_date}.md"
    
    # 构建报告
    report_lines = [
        "# TFA Risk Agent 持续优化报告",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**分析周期**: 最近 {analysis_data.get('period_days', 7)} 天",
        "",
        "## 执行摘要",
        ""
    ]
    
    # 统计数据
    stats = analysis_data.get("statistics", {})
    report_lines.extend([
        f"- **反馈总数**: {stats.get('total_feedbacks', 0)}",
        f"- **修正次数**: {stats.get('corrections_count', 0)}",
        ""
    ])
    
    # 准确率趋势
    trends = analysis_data.get("accuracy_trends", {})
    if trends:
        report_lines.extend([
            "## 准确率趋势",
            "",
            "| 指标 | 当前值 | 趋势 |",
            "|------|--------|------|"
        ])
        
        for key, data in trends.items():
            trend_emoji = {"improving": "📈 提升", "stable": "➡️ 稳定", "declining": "📉 下降"}.get(
                data.get("trend"), "➡️"
            )
            report_lines.append(f"| {key} | {data.get('current', 'N/A')}% | {trend_emoji} |")
        
        report_lines.append("")
    
    # 需要关注的问题
    patterns = analysis_data.get("error_patterns", [])
    high_freq_patterns = [p for p in patterns if p.get("frequency", 0) >= 3]
    
    if high_freq_patterns:
        report_lines.extend([
            "## 需要关注的高频问题",
            ""
        ])
        
        for pattern in high_freq_patterns:
            severity = pattern.get("severity", "low")
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
            report_lines.extend([
                f"### {emoji} {pattern.get('description', 'Unknown')}",
                f"- **出现次数**: {pattern.get('frequency', 0)}",
                f"- **严重程度**: {severity}",
                f"- **影响DDQ**: {', '.join(pattern.get('affected_ddq_ids', [])[:5])}",
                ""
            ])
    
    # 优化建议
    suggestions = analysis_data.get("improvement_suggestions", [])
    if suggestions:
        report_lines.extend([
            "## 优化建议",
            ""
        ])
        
        for i, sugg in enumerate(suggestions[:10], 1):
            priority = sugg.get("priority", "low")
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
            report_lines.extend([
                f"{i}. {emoji} **{sugg.get('category', 'other')}** - {sugg.get('description', '')}",
                f"   - 预期效果: {sugg.get('expected_impact', 'N/A')}",
                f"   - 实现难度: {sugg.get('implementation_complexity', 'unknown')}",
                ""
            ])
    
    # 下一步行动
    report_lines.extend([
        "## 下一步行动",
        "",
        "### 本周执行",
        ""
    ])
    
    high_priority = [s for s in suggestions if s.get("priority") == "high"][:3]
    if high_priority:
        for sugg in high_priority:
            report_lines.append(f"- [ ] {sugg.get('description')}")
    else:
        report_lines.append("- [ ] 持续监控反馈数据")
    
    report_lines.extend([
        "",
        "### 本月目标",
        "",
        "- [ ] 证据定位准确率 > 95%",
        "- [ ] 回答状态判定准确率 > 90%",
        "- [ ] 用户整体满意度 > 4.0/5.0",
        ""
    ])
    
    # 保存报告
    report_content = "\n".join(report_lines)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    return str(report_path)


def update_learning_record(analysis_data: dict):
    """更新学习记录"""
    learning_file = LEARNING_DIR / "corrections.json"
    
    # 加载现有记录
    if learning_file.exists():
        with open(learning_file, 'r', encoding='utf-8') as f:
            learning_data = json.load(f)
    else:
        learning_data = {"corrections": [], "last_updated": None}
    
    # 添加新学习记录
    patterns = analysis_data.get("error_patterns", [])
    for pattern in patterns:
        if pattern.get("frequency", 0) >= 3:
            correction_entry = {
                "correction_id": f"corr_{datetime.now().strftime('%Y%m%d')}_{pattern['pattern_id']}",
                "timestamp": datetime.now().isoformat(),
                "correction_type": pattern["category"],
                "description": pattern["description"],
                "frequency": pattern["frequency"],
                "affected_ddq_ids": pattern.get("affected_ddq_ids", []),
                "rule_derived": f"需要改进{pattern['category']}的处理逻辑",
                "verification_status": "pending"
            }
            learning_data["corrections"].append(correction_entry)
    
    learning_data["last_updated"] = datetime.now().isoformat()
    
    # 保存
    with open(learning_file, 'w', encoding='utf-8') as f:
        json.dump(learning_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 学习记录已更新: {learning_file}")


def generate_task_list(analysis_data: dict) -> str:
    """生成任务清单"""
    task_date = datetime.now().strftime("%Y%m%d")
    task_path = IMPROVEMENTS_DIR / f"tasks_{task_date}.md"
    
    suggestions = analysis_data.get("improvement_suggestions", [])
    
    task_lines = [
        "# TFA Risk Agent 优化任务清单",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "## 高优先级任务",
        ""
    ]
    
    high_priority = [s for s in suggestions if s.get("priority") == "high"]
    for i, sugg in enumerate(high_priority, 1):
        task_lines.extend([
            f"### {i}. {sugg.get('description')}",
            f"- **类型**: {sugg.get('category')}",
            f"- **预期效果**: {sugg.get('expected_impact')}",
            f"- **复杂度**: {sugg.get('implementation_complexity')}",
            f"- **状态**: 🔲 待开始",
            ""
        ])
    
    task_lines.extend([
        "## 中优先级任务",
        ""
    ])
    
    medium_priority = [s for s in suggestions if s.get("priority") == "medium"]
    for i, sugg in enumerate(medium_priority, 1):
        task_lines.extend([
            f"{i}. {sugg.get('description')} [{sugg.get('category')}]",
            ""
        ])
    
    task_content = "\n".join(task_lines)
    with open(task_path, 'w', encoding='utf-8') as f:
        f.write(task_content)
    
    return str(task_path)


def check_accuracy_thresholds(analysis_data: dict) -> bool:
    """检查准确率是否低于阈值，需要告警"""
    trends = analysis_data.get("accuracy_trends", {})
    
    thresholds = {
        "evidence_location": 85,
        "answer_status": 80,
        "tier_level": 85
    }
    
    alerts = []
    for metric, threshold in thresholds.items():
        if metric in trends:
            current = trends[metric].get("current", 100)
            if current < threshold:
                alerts.append(f"⚠️ {metric} 准确率 {current}% 低于阈值 {threshold}%")
    
    if alerts:
        print("\n🚨 准确率告警:")
        for alert in alerts:
            print(f"   {alert}")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description="TFA Risk Agent 持续优化脚本")
    parser.add_argument("--period", default="7d",
                        help="分析周期（如 7d, 30d）")
    parser.add_argument("--auto", action="store_true",
                        help="自动模式（适合cron调用）")
    parser.add_argument("--generate-tasks", action="store_true",
                        help="生成优化任务清单")
    
    args = parser.parse_args()
    
    # 解析周期
    import re
    period_match = re.match(r'(\d+)d', args.period)
    period_days = int(period_match.group(1)) if period_match else 7
    
    print("=" * 60)
    print("TFA Risk Agent 持续优化系统")
    print("=" * 60)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"分析周期: {period_days} 天")
    print("")
    
    # 运行分析
    analysis_data = run_feedback_analysis(period_days)
    
    if not analysis_data:
        print("❌ 分析失败，退出")
        return 1
    
    # 检查阈值
    check_accuracy_thresholds(analysis_data)
    
    # 生成报告
    report_path = generate_improvement_report(analysis_data)
    print(f"✅ 优化报告已生成: {report_path}")
    
    # 更新学习记录
    update_learning_record(analysis_data)
    
    # 生成任务清单
    if args.generate_tasks or args.auto:
        task_path = generate_task_list(analysis_data)
        print(f"✅ 任务清单已生成: {task_path}")
    
    print("\n" + "=" * 60)
    print("优化流程完成")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
