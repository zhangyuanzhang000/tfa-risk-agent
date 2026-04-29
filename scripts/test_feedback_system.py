#!/usr/bin/env python3
"""
TFA Risk Agent 反馈系统测试脚本
验证反馈收集和分析功能
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from feedback_collector import save_instant_feedback, save_assessment_feedback, get_feedback_stats
from feedback_analyzer import FeedbackAnalyzer


def test_feedback_collection():
    """测试反馈收集功能"""
    print("=" * 50)
    print("测试 1: 反馈收集")
    print("=" * 50)
    
    # 测试即时反馈
    print("\n1.1 测试即时反馈收集...")
    instant_data = {
        "item_feedback": [
            {
                "ddq_id": "S1",
                "feedback_type": "evidence_location",
                "is_correct": False,
                "original_value": {
                    "evidence_source": "中粮2024年报.pdf",
                    "page_number": "15"
                },
                "corrected_value": {
                    "evidence_source": "中粮2024年报.pdf",
                    "page_number": "17"
                },
                "correction_reason": "原文在第17页，搜索时漏掉了中间部分"
            },
            {
                "ddq_id": "S3",
                "feedback_type": "tier_level",
                "is_correct": False,
                "original_value": {"evidence_tier": "Tier2"},
                "corrected_value": {"evidence_tier": "Tier1"},
                "correction_reason": "原文直接回答了问题，应属Tier1"
            }
        ],
        "session_context": {
            "files_uploaded": ["中粮2024年报.pdf", "ESG报告.pdf"],
            "assessment_scope": {
                "company": "中粮集团",
                "commodities": ["大豆"],
                "regions": ["巴西", "阿根廷"]
            }
        }
    }
    
    feedback_id1 = save_instant_feedback("test_assessment_001", instant_data)
    print(f"✅ 即时反馈已保存: {feedback_id1}")
    
    # 测试更多即时反馈（用于模式分析）
    print("\n1.2 生成更多测试数据...")
    for i in range(3):
        test_data = {
            "item_feedback": [
                {
                    "ddq_id": f"S{i+1}",
                    "feedback_type": "evidence_location",
                    "is_correct": False,
                    "correction_reason": f"测试反馈 {i+1}"
                }
            ]
        }
        save_instant_feedback("test_assessment_001", test_data)
    print("✅ 生成3条额外的测试反馈")
    
    # 测试评估反馈
    print("\n1.3 测试评估反馈收集...")
    assessment_data = {
        "overall_rating": {"score": 4.2, "nps": 8},
        "stage_ratings": {
            "upload_experience": 5,
            "parsing_accuracy": 4,
            "ddq_coverage": 4.5,
            "report_quality": 4,
            "html_visualization": 4
        },
        "open_feedback": {
            "what_worked": "HTML报告的可视化效果很好，特别是风险热力图",
            "what_needs_improvement": "证据定位有时不够准确，需要手动校对页码",
            "missing_features": "希望能导出PDF格式的报告"
        }
    }
    
    feedback_id2 = save_assessment_feedback("test_assessment_001", assessment_data)
    print(f"✅ 评估反馈已保存: {feedback_id2}")
    
    return True


def test_feedback_stats():
    """测试反馈统计功能"""
    print("\n" + "=" * 50)
    print("测试 2: 反馈统计")
    print("=" * 50)
    
    print("\n2.1 获取最近30天的统计...")
    stats = get_feedback_stats(days=30)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    
    return True


def test_feedback_analysis():
    """测试反馈分析功能"""
    print("\n" + "=" * 50)
    print("测试 3: 反馈分析")
    print("=" * 50)
    
    print("\n3.1 创建分析器并加载反馈...")
    analyzer = FeedbackAnalyzer(period_days=30)
    analyzer.load_feedbacks()
    
    print("\n3.2 分析错误模式...")
    patterns = analyzer.analyze_error_patterns()
    print(f"发现 {len(patterns)} 个错误模式:")
    for p in patterns:
        print(f"  - {p['description']}: {p['frequency']}次 ({p['severity']})")
    
    print("\n3.3 计算准确率趋势...")
    trends = analyzer.calculate_accuracy_trends()
    print("准确率趋势:")
    for key, data in trends.items():
        print(f"  - {key}: {data['current']}% ({data['trend']})")
    
    print("\n3.4 分析用户满意度...")
    satisfaction = analyzer.analyze_satisfaction()
    print(f"满意度分析: {json.dumps(satisfaction, ensure_ascii=False, indent=2)}")
    
    print("\n3.5 生成优化建议...")
    suggestions = analyzer.generate_improvement_suggestions(patterns, trends)
    print(f"生成 {len(suggestions)} 条优化建议:")
    for s in suggestions[:3]:
        print(f"  - [{s['priority']}] {s['description']}")
    
    print("\n3.6 生成分析报告...")
    report = analyzer.generate_report()
    # 只显示报告的前1000字符
    print(report[:1000] + "...")
    
    return True


def test_embedder():
    """测试HTML嵌入组件"""
    print("\n" + "=" * 50)
    print("测试 4: HTML反馈组件")
    print("=" * 50)
    
    from feedback_embedder import FeedbackEmbedder
    
    print("\n4.1 创建反馈嵌入器...")
    embedder = FeedbackEmbedder("test_assessment_001", "user_001")
    
    print("\n4.2 生成DDQ反馈组件...")
    ddq_feedback = embedder.generate_ddq_feedback_component("S1")
    print(f"DDQ反馈组件长度: {len(ddq_feedback)} 字符")
    
    print("\n4.3 生成报告末尾反馈组件...")
    report_feedback = embedder.generate_report_end_feedback()
    print(f"报告反馈组件长度: {len(report_feedback)} 字符")
    
    print("\n4.4 测试注入到HTML报告...")
    test_html = """<!DOCTYPE html>
<html>
<head><title>Test Report</title></head>
<body>
<h1>Test Report</h1>
<p>This is a test report.</p>
</body>
</html>"""
    
    result_html = embedder.inject_into_report(test_html)
    print(f"注入后HTML长度: {len(result_html)} 字符")
    
    # 保存测试报告
    test_output = Path(__file__).parent.parent / "feedback" / "test_report_with_feedback.html"
    with open(test_output, 'w', encoding='utf-8') as f:
        f.write(result_html)
    print(f"✅ 测试报告已保存: {test_output}")
    
    return True


def cleanup_test_data():
    """清理测试数据"""
    print("\n" + "=" * 50)
    print("清理测试数据")
    print("=" * 50)
    
    feedback_dir = Path(__file__).parent.parent / "feedback"
    
    # 删除测试反馈文件
    for subdir in ["instant", "assessment"]:
        dir_path = feedback_dir / subdir
        if dir_path.exists():
            for file_path in dir_path.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # 只删除测试数据
                    if data.get("assessment_id", "").startswith("test_"):
                        file_path.unlink()
                        print(f"  删除: {file_path.name}")
                except:
                    pass
    
    # 删除测试报告
    test_report = feedback_dir / "test_report_with_feedback.html"
    if test_report.exists():
        test_report.unlink()
        print(f"  删除: {test_report.name}")
    
    print("✅ 测试数据已清理")


def main():
    """主测试函数"""
    print("=" * 50)
    print("TFA Risk Agent 反馈系统测试")
    print("=" * 50)
    
    try:
        # 运行所有测试
        test_feedback_collection()
        test_feedback_stats()
        test_feedback_analysis()
        test_embedder()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试通过！")
        print("=" * 50)
        
        # 询问是否清理测试数据
        response = input("\n是否清理测试数据? (y/n): ").strip().lower()
        if response == 'y':
            cleanup_test_data()
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
