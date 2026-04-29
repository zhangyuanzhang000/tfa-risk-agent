#!/usr/bin/env python3
"""
TFA Risk Agent 反馈收集器
用于收集和存储用户反馈

用法:
    # 收集即时反馈
    python3 feedback_collector.py --type instant --assessment-id asm_xxx --data '{...}'
    
    # 收集评估反馈
    python3 feedback_collector.py --type assessment --assessment-id asm_xxx --data '{...}'
    
    # 从文件批量导入
    python3 feedback_collector.py --import-file feedback_batch.json
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# 反馈数据目录
FEEDBACK_DIR = Path(__file__).parent.parent / "feedback"
LEARNING_DIR = Path(__file__).parent.parent / "learning"


def generate_id(prefix: str) -> str:
    """生成带时间戳的唯一ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}"


def save_instant_feedback(assessment_id: str, data: dict) -> str:
    """保存即时反馈"""
    feedback_id = generate_id("fb")
    
    feedback_record = {
        "feedback_id": feedback_id,
        "assessment_id": assessment_id,
        "timestamp": datetime.now().isoformat(),
        **data
    }
    
    # 保存到instant目录
    output_path = FEEDBACK_DIR / "instant" / f"{feedback_id}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(feedback_record, f, ensure_ascii=False, indent=2)
    
    # 同时追加到学习日志
    _append_to_learning_log("instant", feedback_record)
    
    print(f"✅ 即时反馈已保存: {feedback_id}")
    return feedback_id


def save_assessment_feedback(assessment_id: str, data: dict) -> str:
    """保存评估完成后的整体反馈"""
    feedback_id = generate_id("afb")
    
    feedback_record = {
        "feedback_id": feedback_id,
        "assessment_id": assessment_id,
        "timestamp": datetime.now().isoformat(),
        **data
    }
    
    # 保存到assessment目录
    output_path = FEEDBACK_DIR / "assessment" / f"{feedback_id}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(feedback_record, f, ensure_ascii=False, indent=2)
    
    # 同时追加到学习日志
    _append_to_learning_log("assessment", feedback_record)
    
    print(f"✅ 评估反馈已保存: {feedback_id}")
    return feedback_id


def _append_to_learning_log(feedback_type: str, record: dict):
    """追加记录到学习日志"""
    log_path = LEARNING_DIR / "accuracy_log.jsonl"
    
    log_entry = {
        "type": feedback_type,
        "timestamp": record["timestamp"],
        "feedback_id": record["feedback_id"],
        "assessment_id": record.get("assessment_id"),
        "has_correction": _has_correction(record)
    }
    
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


def _has_correction(record: dict) -> bool:
    """检查反馈是否包含修正"""
    if "item_feedback" in record:
        for item in record["item_feedback"]:
            if not item.get("is_correct", True):
                return True
    return False


def load_feedback_by_assessment(assessment_id: str) -> list:
    """加载特定评估的所有反馈"""
    feedbacks = []
    
    # 搜索instant目录
    for file_path in (FEEDBACK_DIR / "instant").glob("*.json"):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data.get("assessment_id") == assessment_id:
                feedbacks.append(data)
    
    # 搜索assessment目录
    for file_path in (FEEDBACK_DIR / "assessment").glob("*.json"):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data.get("assessment_id") == assessment_id:
                feedbacks.append(data)
    
    return feedbacks


def get_feedback_stats(days: int = 30) -> dict:
    """获取反馈统计信息"""
    from datetime import timedelta, timezone
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    stats = {
        "period_days": days,
        "total_instant": 0,
        "total_assessment": 0,
        "corrections_count": 0,
        "average_ratings": {}
    }
    
    # 统计即时反馈
    for file_path in (FEEDBACK_DIR / "instant").glob("*.json"):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            feedback_time = datetime.fromisoformat(data["timestamp"])
            # 确保feedback_time有时区信息
            if feedback_time.tzinfo is None:
                feedback_time = feedback_time.replace(tzinfo=timezone.utc)
            if feedback_time >= cutoff_date:
                stats["total_instant"] += 1
                if _has_correction(data):
                    stats["corrections_count"] += 1
    
    # 统计评估反馈
    ratings_sum = {key: 0 for key in ["upload_experience", "parsing_accuracy", 
                                       "ddq_coverage", "report_quality", "html_visualization"]}
    ratings_count = 0
    
    for file_path in (FEEDBACK_DIR / "assessment").glob("*.json"):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            feedback_time = datetime.fromisoformat(data["timestamp"])
            # 确保feedback_time有时区信息
            if feedback_time.tzinfo is None:
                feedback_time = feedback_time.replace(tzinfo=timezone.utc)
            if feedback_time >= cutoff_date:
                stats["total_assessment"] += 1
                if "stage_ratings" in data:
                    ratings_count += 1
                    for key in ratings_sum:
                        if key in data["stage_ratings"]:
                            ratings_sum[key] += data["stage_ratings"][key]
    
    # 计算平均分
    if ratings_count > 0:
        stats["average_ratings"] = {
            key: round(ratings_sum[key] / ratings_count, 2) 
            for key in ratings_sum
        }
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="TFA Risk Agent 反馈收集器")
    parser.add_argument("--type", choices=["instant", "assessment"], 
                        help="反馈类型")
    parser.add_argument("--assessment-id", 
                        help="评估ID")
    parser.add_argument("--data", 
                        help="反馈数据（JSON字符串）")
    parser.add_argument("--import-file", 
                        help="从文件批量导入")
    parser.add_argument("--stats", action="store_true",
                        help="显示统计信息")
    parser.add_argument("--days", type=int, default=30,
                        help="统计时间范围（天）")
    
    args = parser.parse_args()
    
    if args.stats:
        stats = get_feedback_stats(args.days)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return
    
    if args.import_file:
        with open(args.import_file, 'r', encoding='utf-8') as f:
            batch = json.load(f)
        for item in batch:
            if item.get("type") == "instant":
                save_instant_feedback(item["assessment_id"], item["data"])
            elif item.get("type") == "assessment":
                save_assessment_feedback(item["assessment_id"], item["data"])
        return
    
    if not args.type or not args.assessment_id:
        parser.print_help()
        return
    
    data = json.loads(args.data) if args.data else {}
    
    if args.type == "instant":
        save_instant_feedback(args.assessment_id, data)
    elif args.type == "assessment":
        save_assessment_feedback(args.assessment_id, data)


if __name__ == "__main__":
    main()
