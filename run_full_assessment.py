#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TFA Risk Agent - 完整工作流脚本 v1.0
端到端自动化：PDF提取 → DDQ评估表生成 → 人工审核提示 → 报告生成

使用方法:
    python3 run_full_assessment.py --pdf /path/to/report.pdf --company "企业名称"
    python3 run_full_assessment.py --ddq /path/to/ddq_assessment.csv --company "企业名称"

工作流程:
    1. 从PDF/Word提取证据（extract_evidence.py）
    2. 生成DDQ评估表（Excel/CSV）
    3. 提示人工审核
    4. 生成TFA风险评估报告（report_generator_v3.1.py）
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加scripts目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / 'scripts'))

from extract_evidence import EvidenceExtractor
from report_generator_v3 import TFARiskReportGenerator


def print_step(step_num, title):
    """打印步骤标题"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {title}")
    print('='*60)


def step1_extract_evidence(pdf_path: str, output_dir: Path, company_name: str) -> Path:
    """
    步骤1：从PDF提取证据
    """
    print_step(1, "从PDF/Word报告提取证据")
    
    if not os.path.exists(pdf_path):
        print(f"❌ 文件不存在: {pdf_path}")
        sys.exit(1)
    
    print(f"📄 输入文件: {pdf_path}")
    print(f"🏢 企业名称: {company_name}")
    print("⏳ 正在提取文本和匹配DDQ关键词...")
    
    try:
        extractor = EvidenceExtractor(pdf_path)
        
        # 提取文本
        text, pages = extractor.extract()
        print(f"✅ 已提取 {len(pages)} 页/段落，共 {len(text)} 字符")
        
        # 生成DDQ评估表
        timestamp = datetime.now().strftime('%Y%m%d')
        output_csv = output_dir / f"{company_name}_DDQ评估表_初稿_{timestamp}.csv"
        extractor.generate_ddq_csv(str(output_csv))
        
        print(f"✅ DDQ评估表已生成: {output_csv}")
        
        # 显示统计
        ddq_data = extractor.extract_all_ddq()
        total_evidence = sum(len(v) for v in ddq_data.values())
        tier1_count = sum(len([e for e in v if e['evidence_tier'] == 'Tier1']) for v in ddq_data.values())
        
        print(f"\n📊 证据统计:")
        print(f"  - 匹配DDQ问题数: {len(ddq_data)}")
        print(f"  - 总证据条数: {total_evidence}")
        print(f"  - Tier1 (直接证据): {tier1_count}")
        print(f"  - Tier2/3 (间接/背景): {total_evidence - tier1_count}")
        
        return output_csv
        
    except Exception as e:
        print(f"❌ 提取失败: {e}")
        sys.exit(1)


def step2_prompt_manual_review(ddq_csv_path: Path):
    """
    步骤2：提示人工审核
    """
    print_step(2, "人工审核DDQ评估表")
    
    print("""
📋 请对DDQ评估表进行人工审核:

审核步骤:
1. 打开生成的CSV文件（可用Excel编辑）
2. 检查每一行的"证据原文"列，确认是否准确
3. 在"审核状态"列填写: 接受 / 修改 / 拒绝
4. 如选择"修改"或"拒绝"，请在"审核备注"列填写理由

审核标准:
- 接受: 证据充分，准确回答问题
- 修改: 证据需要调整或补充
- 拒绝: 证据不足或不当

重要提示:
⚠️ 审核状态为"修改"或"拒绝"时，必须填写审核备注
⚠️ 建议关注Tier3（背景信息）标注的问题，可能需要补充证据

审核完成后，保存文件并继续进行下一步。
""")
    
    input(f"\n按 Enter 键确认已完成审核: {ddq_csv_path}")
    
    # 检查文件是否存在（用户可能重命名）
    if not ddq_csv_path.exists():
        # 尝试找到最新的DDQ评估表
        output_dir = ddq_csv_path.parent
        company_name = ddq_csv_path.stem.split('_')[0]
        csv_files = list(output_dir.glob(f"{company_name}_DDQ评估表_*.csv"))
        
        if csv_files:
            ddq_csv_path = max(csv_files, key=lambda p: p.stat().st_mtime)
            print(f"✅ 检测到最新文件: {ddq_csv_path}")
        else:
            print(f"❌ 找不到DDQ评估表文件")
            sys.exit(1)
    
    return ddq_csv_path


def step3_generate_report(ddq_csv_path: Path, output_dir: Path, company_name: str) -> Path:
    """
    步骤3：生成TFA风险评估报告
    """
    print_step(3, "生成TFA风险评估报告")
    
    print(f"📊 正在基于DDQ评估表计算风险指标...")
    
    try:
        generator = TFARiskReportGenerator(
            ddq_csv_path=str(ddq_csv_path),
            output_dir=str(output_dir),
            company_name=company_name
        )
        
        report_path = generator.generate_html_report()
        
        print(f"\n✅ 报告生成成功!")
        print(f"📄 报告路径: {report_path}")
        
        return Path(report_path)
        
    except Exception as e:
        print(f"❌ 报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def step4_final_deliverables(ddq_csv_path: Path, report_path: Path, output_dir: Path, company_name: str):
    """
    步骤4：整理最终交付包
    """
    print_step(4, "整理最终交付包")
    
    timestamp = datetime.now().strftime('%Y%m%d')
    deliverables_dir = output_dir / f"{company_name}_TFA风险评估包_{timestamp}"
    deliverables_dir.mkdir(exist_ok=True)
    
    # 复制文件到交付包
    import shutil
    
    # 1. DDQ评估表（重命名为最终版）
    final_ddq = deliverables_dir / f"01_DDQ尽调评估表_最终版.csv"
    shutil.copy(ddq_csv_path, final_ddq)
    print(f"✅ 01_DDQ尽调评估表_最终版.csv")
    
    # 2. HTML报告
    final_report = deliverables_dir / f"02_TFA风险评估报告.html"
    shutil.copy(report_path, final_report)
    print(f"✅ 02_TFA风险评估报告.html")
    
    # 3. 生成数据缺口清单（从DDQ中提取）
    gaps_csv = deliverables_dir / f"03_数据缺口清单.csv"
    generate_data_gaps_csv(ddq_csv_path, gaps_csv)
    print(f"✅ 03_数据缺口清单.csv")
    
    # 4. 生成证据索引
    index_csv = deliverables_dir / f"04_证据索引.csv"
    generate_evidence_index(ddq_csv_path, index_csv)
    print(f"✅ 04_证据索引.csv")
    
    print(f"\n📦 最终交付包已整理: {deliverables_dir}")
    print("\n交付清单:")
    print("  1. DDQ尽调评估表_最终版.csv - 人工审核后的评估表")
    print("  2. TFA风险评估报告.html - 交互式可视化报告")
    print("  3. 数据缺口清单.csv - 识别出的数据缺口")
    print("  4. 证据索引.csv - 证据来源文件和位置索引")
    
    return deliverables_dir


def generate_data_gaps_csv(ddq_csv_path: Path, output_path: Path):
    """生成数据缺口清单"""
    import csv
    
    gaps = []
    with open(ddq_csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            status = row.get('审核状态', '')
            if status in ['拒绝', '修改']:
                gaps.append({
                    '缺口编号': f"GAP-{i:03d}",
                    '对应DDQ': row.get('DDQ编号', ''),
                    '问题分类': row.get('问题分类', ''),
                    '缺口描述': row.get('审核备注', '未填写理由'),
                    '优先级': '高' if row.get('证据等级') == 'Tier3' else '中'
                })
    
    if gaps:
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=gaps[0].keys())
            writer.writeheader()
            writer.writerows(gaps)
    else:
        # 创建空模板
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['缺口编号', '对应DDQ', '问题分类', '缺口描述', '优先级'])
            writer.writerow(['GAP-001', '示例', '示例', '未发现明显数据缺口', '低'])


def generate_evidence_index(ddq_csv_path: Path, output_path: Path):
    """生成证据索引"""
    import csv
    
    index = []
    with open(ddq_csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('证据原文'):
                index.append({
                    'DDQ编号': row.get('DDQ编号', ''),
                    '问题分类': row.get('问题分类', ''),
                    '证据来源文件': row.get('证据来源文件', ''),
                    '页码/段落': row.get('页码/段落', ''),
                    '证据等级': row.get('证据等级', ''),
                    '回答状态': row.get('回答状态', '')
                })
    
    if index:
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=index[0].keys())
            writer.writeheader()
            writer.writerows(index)


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='TFA Risk Agent - 完整工作流脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 从PDF开始完整流程
  python3 run_full_assessment.py --pdf /path/to/report.pdf --company "中粮国际"
  
  # 从DDQ评估表开始（跳过PDF提取）
  python3 run_full_assessment.py --ddq /path/to/ddq.csv --company "中粮国际"
  
  # 指定输出目录
  python3 run_full_assessment.py --pdf report.pdf --company "中粮国际" --output ./my_output
        """
    )
    
    parser.add_argument('--pdf', help='输入PDF/Word报告文件路径')
    parser.add_argument('--ddq', help='输入DDQ评估表CSV文件路径（跳过PDF提取）')
    parser.add_argument('--company', '-c', required=True, help='企业名称')
    parser.add_argument('--output', '-o', default='./output', help='输出目录（默认：./output）')
    
    args = parser.parse_args()
    
    # 验证参数
    if not args.pdf and not args.ddq:
        parser.error("必须提供 --pdf 或 --ddq 参数之一")
    
    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║     TFA Risk Agent - 可持续供应链风险评估工作流           ║
║                                                            ║
║     版本: v1.0 | 基于 TFA Due Diligence Framework        ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    print(f"🏢 企业名称: {args.company}")
    print(f"📁 输出目录: {output_dir.absolute()}")
    
    try:
        if args.pdf:
            # 完整流程：PDF → DDQ → 报告
            ddq_csv_path = step1_extract_evidence(args.pdf, output_dir, args.company)
            ddq_csv_path = step2_prompt_manual_review(ddq_csv_path)
            report_path = step3_generate_report(ddq_csv_path, output_dir, args.company)
            deliverables_dir = step4_final_deliverables(ddq_csv_path, report_path, output_dir, args.company)
            
        elif args.ddq:
            # 跳过PDF提取：DDQ → 报告
            ddq_csv_path = Path(args.ddq)
            if not ddq_csv_path.exists():
                print(f"❌ DDQ评估表不存在: {ddq_csv_path}")
                sys.exit(1)
            
            print(f"📄 使用已有DDQ评估表: {ddq_csv_path}")
            report_path = step3_generate_report(ddq_csv_path, output_dir, args.company)
            deliverables_dir = step4_final_deliverables(ddq_csv_path, report_path, output_dir, args.company)
        
        print(f"""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║     ✅ 工作流完成！                                         ║
║                                                            ║
║     交付包位置: {deliverables_dir}
║                                                            ║
╚════════════════════════════════════════════════════════════╝
        """)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
