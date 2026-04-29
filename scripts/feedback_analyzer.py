#!/usr/bin/env python3
"""
TFA Risk Agent 反馈分析器
分析历史反馈，识别错误模式，生成优化建议

用法:
    # 分析最近7天的反馈
    python3 feedback_analyzer.py --period 7d
    
    # 分析最近30天的反馈并生成报告
    python3 feedback_analyzer.py --period 30d --output report.md
    
    # 分析特定评估的反馈
    python3 feedback_analyzer.py --assessment-id asm_xxx
    
    # 比较两个时期的反馈
    python3 feedback_analyzer.py --compare --period1 7d --period2 30d
"""

import json
import os
import re
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Any

# 反馈数据目录
FEEDBACK_DIR = Path(__file__).parent.parent / "feedback"
LEARNING_DIR = Path(__file__).parent.parent / "learning"


class FeedbackAnalyzer:
    """反馈分析器主类"""
    
    def __init__(self, period_days: int = 30):
        self.period_days = period_days
        self.cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)
        self.instant_feedbacks: List[Dict] = []
        self.assessment_feedbacks: List[Dict] = []
        
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """解析时间戳字符串，确保返回带时区的datetime"""
        # 处理Z后缀
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(timestamp_str)
        # 如果没有时区信息，添加UTC时区
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    
    def load_feedbacks(self):
        """加载指定时间范围内的所有反馈"""
        # 加载即时反馈
        instant_dir = FEEDBACK_DIR / "instant"
        if instant_dir.exists():
            for file_path in instant_dir.glob("*.json"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    feedback_time = self._parse_timestamp(data["timestamp"])
                    if feedback_time >= self.cutoff_date:
                        self.instant_feedbacks.append(data)
        
        # 加载评估反馈
        assessment_dir = FEEDBACK_DIR / "assessment"
        if assessment_dir.exists():
            for file_path in assessment_dir.glob("*.json"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    feedback_time = self._parse_timestamp(data["timestamp"])
                    if feedback_time >= self.cutoff_date:
                        self.assessment_feedbacks.append(data)
        
        print(f"📊 加载了 {len(self.instant_feedbacks)} 条即时反馈，{len(self.assessment_feedbacks)} 条评估反馈")
    
    def analyze_error_patterns(self) -> List[Dict]:
        """分析错误模式"""
        patterns = defaultdict(lambda: {"count": 0, "examples": [], "ddq_ids": set()})
        
        for feedback in self.instant_feedbacks:
            for item in feedback.get("item_feedback", []):
                if item.get("is_correct", True):
                    continue  # 跳过正确的反馈
                
                feedback_type = item.get("feedback_type", "other")
                
                # 按类型分类
                if feedback_type == "evidence_location":
                    pattern_key = "evidence_location_error"
                    pattern_desc = "证据定位不准确（文件或页码错误）"
                elif feedback_type == "answer_status":
                    pattern_key = "answer_status_misclassification"
                    pattern_desc = "回答状态判定错误"
                elif feedback_type == "tier_level":
                    pattern_key = "tier_level_misclassification"
                    pattern_desc = "证据等级划分不当"
                else:
                    pattern_key = f"other_{feedback_type}"
                    pattern_desc = f"其他问题: {feedback_type}"
                
                patterns[pattern_key]["count"] += 1
                patterns[pattern_key]["description"] = pattern_desc
                patterns[pattern_key]["category"] = feedback_type
                patterns[pattern_key]["ddq_ids"].add(item.get("ddq_id", "unknown"))
                
                # 保存示例
                if len(patterns[pattern_key]["examples"]) < 3:
                    patterns[pattern_key]["examples"].append({
                        "feedback_id": feedback["feedback_id"],
                        "assessment_id": feedback["assessment_id"],
                        "ddq_id": item.get("ddq_id"),
                        "correction_reason": item.get("correction_reason", "")
                    })
        
        # 转换为列表并排序
        pattern_list = []
        for key, data in patterns.items():
            severity = "high" if data["count"] >= 5 else "medium" if data["count"] >= 2 else "low"
            pattern_list.append({
                "pattern_id": key,
                "category": data["category"],
                "description": data["description"],
                "frequency": data["count"],
                "severity": severity,
                "affected_ddq_ids": list(data["ddq_ids"]),
                "example_cases": data["examples"]
            })
        
        pattern_list.sort(key=lambda x: x["frequency"], reverse=True)
        return pattern_list
    
    def calculate_accuracy_trends(self) -> Dict[str, Any]:
        """计算准确率趋势"""
        # 本期统计
        total_items = 0
        correct_items = 0
        
        category_stats = defaultdict(lambda: {"total": 0, "correct": 0})
        
        for feedback in self.instant_feedbacks:
            for item in feedback.get("item_feedback", []):
                total_items += 1
                feedback_type = item.get("feedback_type", "other")
                category_stats[feedback_type]["total"] += 1
                
                if item.get("is_correct", True):
                    correct_items += 1
                    category_stats[feedback_type]["correct"] += 1
        
        # 计算本期准确率
        current_accuracy = {
            "overall": round(correct_items / total_items * 100, 2) if total_items > 0 else 100,
            "evidence_location": self._calc_category_accuracy(category_stats, "evidence_location"),
            "answer_status": self._calc_category_accuracy(category_stats, "answer_status"),
            "tier_level": self._calc_category_accuracy(category_stats, "tier_level")
        }
        
        # 加载上期数据进行比较
        previous_accuracy = self._load_previous_accuracy()
        
        # 计算趋势
        trends = {}
        for key in current_accuracy:
            current = current_accuracy[key]
            previous = previous_accuracy.get(key, current)
            
            if current > previous + 2:
                trend = "improving"
            elif current < previous - 2:
                trend = "declining"
            else:
                trend = "stable"
            
            trends[key] = {
                "current": current,
                "previous": previous,
                "trend": trend,
                "change": round(current - previous, 2)
            }
        
        return trends
    
    def _calc_category_accuracy(self, stats: Dict, category: str) -> float:
        """计算特定类别的准确率"""
        if category not in stats or stats[category]["total"] == 0:
            return 100.0
        return round(stats[category]["correct"] / stats[category]["total"] * 100, 2)
    
    def _load_previous_accuracy(self) -> Dict:
        """加载上期的准确率数据"""
        log_path = LEARNING_DIR / "accuracy_log.jsonl"
        if not log_path.exists():
            return {}
        
        # 获取上一个分析周期的数据
        prev_cutoff = self.cutoff_date - timedelta(days=self.period_days)
        
        corrections = 0
        total = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_time = self._parse_timestamp(entry["timestamp"])
                    if prev_cutoff <= entry_time < self.cutoff_date:
                        total += 1
                        if entry.get("has_correction"):
                            corrections += 1
                except:
                    continue
        
        if total == 0:
            return {"overall": 100}
        
        return {"overall": round((total - corrections) / total * 100, 2)}
    
    def analyze_satisfaction(self) -> Dict[str, Any]:
        """分析用户满意度"""
        if not self.assessment_feedbacks:
            return {"message": "暂无评估反馈数据"}
        
        overall_scores = []
        stage_scores = defaultdict(list)
        
        for feedback in self.assessment_feedbacks:
            if "overall_rating" in feedback:
                overall_scores.append(feedback["overall_rating"].get("score", 0))
            
            if "stage_ratings" in feedback:
                for key, value in feedback["stage_ratings"].items():
                    stage_scores[key].append(value)
        
        # 计算平均分
        satisfaction = {
            "overall_average": round(sum(overall_scores) / len(overall_scores), 2) if overall_scores else 0,
            "total_responses": len(self.assessment_feedbacks),
            "stage_averages": {
                key: round(sum(values) / len(values), 2) if values else 0
                for key, values in stage_scores.items()
            }
        }
        
        # 识别薄弱环节
        weak_stages = [
            key for key, value in satisfaction["stage_averages"].items()
            if value < 3.5
        ]
        satisfaction["weak_areas"] = weak_stages
        
        return satisfaction
    
    def generate_improvement_suggestions(self, patterns: List[Dict], trends: Dict) -> List[Dict]:
        """基于分析结果生成优化建议"""
        suggestions = []
        
        # 基于错误模式生成建议
        for pattern in patterns:
            if pattern["frequency"] >= 3:
                suggestion = self._pattern_to_suggestion(pattern)
                if suggestion:
                    suggestions.append(suggestion)
        
        # 基于趋势生成建议
        for category, trend_data in trends.items():
            if trend_data.get("trend") == "declining":
                suggestions.append({
                    "suggestion_id": f"trend_{category}",
                    "category": "prompt_optimization",
                    "priority": "high",
                    "description": f"{category}准确率下降 {abs(trend_data['change'])}%，需要优化相关prompt",
                    "expected_impact": f"将{category}准确率从{trend_data['current']}%提升至{trend_data['previous']}%以上",
                    "implementation_complexity": "medium",
                    "related_patterns": [p["pattern_id"] for p in patterns if p["category"] == category]
                })
        
        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda x: priority_order.get(x["priority"], 3))
        
        return suggestions
    
    def _pattern_to_suggestion(self, pattern: Dict) -> Dict:
        """将错误模式转换为优化建议"""
        pattern_id = pattern["pattern_id"]
        
        suggestion_map = {
            "evidence_location_error": {
                "category": "prompt_optimization",
                "description": "优化证据定位的prompt，要求更精确地提取页码和段落信息",
                "expected_impact": "减少证据定位错误，提升用户信任度",
                "complexity": "medium"
            },
            "answer_status_misclassification": {
                "category": "rule_update",
                "description": "更新回答状态判定规则，明确'已回答'、'部分回答'、'未找到'的边界",
                "expected_impact": "提升回答状态判定的一致性和准确性",
                "complexity": "medium"
            },
            "tier_level_misclassification": {
                "category": "rule_update",
                "description": "细化证据等级（Tier1/Tier2/Tier3）的判定标准，提供更多示例",
                "expected_impact": "统一证据等级判定标准",
                "complexity": "easy"
            }
        }
        
        if pattern_id in suggestion_map:
            mapped = suggestion_map[pattern_id]
            return {
                "suggestion_id": f"sugg_{pattern_id}",
                "category": mapped["category"],
                "priority": "high" if pattern["severity"] == "high" else "medium",
                "description": mapped["description"],
                "expected_impact": mapped["expected_impact"],
                "implementation_complexity": mapped["complexity"],
                "related_patterns": [pattern_id]
            }
        
        return None
    
    def generate_report(self) -> str:
        """生成分析报告"""
        # 执行分析
        patterns = self.analyze_error_patterns()
        trends = self.calculate_accuracy_trends()
        satisfaction = self.analyze_satisfaction()
        suggestions = self.generate_improvement_suggestions(patterns, trends)
        
        # 构建报告
        report = []
        report.append("# TFA Risk Agent 反馈分析报告")
        report.append(f"\n**分析周期**: 最近 {self.period_days} 天")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**数据来源**: {len(self.instant_feedbacks)} 条即时反馈，{len(self.assessment_feedbacks)} 条评估反馈")
        
        # 准确率趋势
        report.append("\n## 一、准确率趋势\n")
        report.append("| 指标 | 当前 | 上期 | 变化 | 趋势 |")
        report.append("|------|------|------|------|------|")
        
        for key, data in trends.items():
            trend_emoji = {"improving": "📈", "stable": "➡️", "declining": "📉"}.get(data["trend"], "➡️")
            change_sign = "+" if data["change"] > 0 else ""
            report.append(f"| {key} | {data['current']}% | {data['previous']}% | {change_sign}{data['change']}% | {trend_emoji} {data['trend']} |")
        
        # 错误模式分析
        report.append("\n## 二、高频错误模式\n")
        if patterns:
            for i, pattern in enumerate(patterns[:5], 1):
                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(pattern["severity"], "⚪")
                report.append(f"### {i}. {severity_emoji} {pattern['description']}")
                report.append(f"- **出现次数**: {pattern['frequency']}")
                report.append(f"- **严重程度**: {pattern['severity']}")
                report.append(f"- **影响DDQ**: {', '.join(pattern['affected_ddq_ids'][:5])}")
                
                if pattern["example_cases"]:
                    report.append("- **典型案例**:")
                    for ex in pattern["example_cases"][:2]:
                        reason = ex.get("correction_reason", "")
                        if reason:
                            report.append(f"  - {ex['ddq_id']}: {reason}")
                report.append("")
        else:
            report.append("✅ 未发现明显错误模式")
        
        # 用户满意度
        report.append("\n## 三、用户满意度\n")
        if isinstance(satisfaction, dict) and "overall_average" in satisfaction:
            report.append(f"- **整体评分**: {satisfaction['overall_average']}/5.0")
            report.append(f"- **反馈数量**: {satisfaction['total_responses']} 份")
            report.append("\n**各环节评分**:")
            for stage, score in satisfaction.get("stage_averages", {}).items():
                bar = "█" * int(score) + "░" * (5 - int(score))
                report.append(f"- {stage}: {score}/5.0 {bar}")
            
            if satisfaction.get("weak_areas"):
                report.append(f"\n⚠️ **需要改进的环节**: {', '.join(satisfaction['weak_areas'])}")
        else:
            report.append(str(satisfaction))
        
        # 优化建议
        report.append("\n## 四、优化建议\n")
        if suggestions:
            for i, sugg in enumerate(suggestions[:10], 1):
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sugg["priority"], "⚪")
                report.append(f"### {i}. {priority_emoji} [{sugg['category']}] {sugg['description']}")
                report.append(f"- **预期效果**: {sugg['expected_impact']}")
                report.append(f"- **实现难度**: {sugg['implementation_complexity']}")
                report.append("")
        else:
            report.append("✅ 暂无紧急优化建议")
        
        # 下一步行动
        report.append("\n## 五、下一步行动\n")
        high_priority = [s for s in suggestions if s["priority"] == "high"]
        if high_priority:
            report.append("### 高优先级行动:")
            for sugg in high_priority[:3]:
                report.append(f"1. [{sugg['category']}] {sugg['description']}")
        
        report.append("\n### 建议的监控指标:")
        report.append("- 证据定位准确率（目标: >95%）")
        report.append("- 回答状态判定准确率（目标: >90%）")
        report.append("- 用户整体满意度（目标: >4.0/5.0）")
        report.append("- 平均反馈响应时间（目标: <24小时）")
        
        return "\n".join(report)
    
    def save_analysis(self, output_path: Path = None):
        """保存分析结果到文件"""
        analysis_data = {
            "analysis_id": f"pa_{datetime.now().strftime('%Y%m%d')}",
            "analysis_date": datetime.now().isoformat(),
            "period_days": self.period_days,
            "statistics": {
                "total_feedbacks": len(self.instant_feedbacks) + len(self.assessment_feedbacks),
                "corrections_count": sum(
                    1 for f in self.instant_feedbacks 
                    for item in f.get("item_feedback", []) 
                    if not item.get("is_correct", True)
                )
            },
            "error_patterns": self.analyze_error_patterns(),
            "accuracy_trends": self.calculate_accuracy_trends(),
            "satisfaction": self.analyze_satisfaction(),
            "improvement_suggestions": self.generate_improvement_suggestions(
                self.analyze_error_patterns(),
                self.calculate_accuracy_trends()
            )
        }
        
        if output_path is None:
            output_path = FEEDBACK_DIR / "patterns" / f"patterns_{datetime.now().strftime('%Y%m%d')}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        
        return output_path


def main():
    parser = argparse.ArgumentParser(description="TFA Risk Agent 反馈分析器")
    parser.add_argument("--period", default="30d",
                        help="分析周期（如 7d, 30d）")
    parser.add_argument("--assessment-id",
                        help="分析特定评估的反馈")
    parser.add_argument("--output",
                        help="输出报告文件路径")
    parser.add_argument("--save-analysis", action="store_true",
                        help="保存分析结果到JSON文件")
    
    args = parser.parse_args()
    
    # 解析周期
    period_match = re.match(r'(\d+)d', args.period)
    if period_match:
        period_days = int(period_match.group(1))
    else:
        period_days = 30
    
    # 创建分析器
    analyzer = FeedbackAnalyzer(period_days=period_days)
    analyzer.load_feedbacks()
    
    if args.assessment_id:
        # 分析特定评估
        feedbacks = [f for f in analyzer.instant_feedbacks 
                    if f.get("assessment_id") == args.assessment_id]
        print(f"找到 {len(feedbacks)} 条相关反馈")
        for f in feedbacks:
            print(json.dumps(f, ensure_ascii=False, indent=2))
        return
    
    # 生成报告
    report = analyzer.generate_report()
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ 报告已保存到: {args.output}")
    else:
        print(report)
    
    # 保存分析数据
    if args.save_analysis:
        analysis_path = analyzer.save_analysis()
        print(f"✅ 分析数据已保存到: {analysis_path}")


if __name__ == "__main__":
    main()
