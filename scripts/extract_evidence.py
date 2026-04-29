#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TFA Risk Agent - PDF/Word 证据提取脚本 v1.0
从企业报告中自动提取DDQ相关证据文本
"""

import re
import fitz  # PyMuPDF
import docx
from pathlib import Path
from typing import List, Dict, Tuple
import csv


class EvidenceExtractor:
    """证据提取器 - 从PDF/Word文档中提取DDQ相关证据"""
    
    # DDQ关键词映射表（用于全文检索）
    DDQ_KEYWORDS = {
        # Core DDQ 关键词
        'C1': ['NDPE', '无毁林', '无泥炭地', '无剥削', '可持续采购承诺', 'deforestation-free', 'peatland', 'exploitation'],
        'C2': ['供应商名单', '供应链透明度', '地理分布', '供应商披露', 'supplier list', 'supply chain transparency'],
        'C3': ['溯源系统', '可追溯', '农场级', 'traceability', 'traceable', 'farm-level', 'origin tracking'],
        'C4': ['高风险地区', '森林风险', '毁林风险', 'high risk area', 'deforestation risk', 'forest risk'],
        'C5': ['合规监测', '卫星监测', '毁林监测', 'compliance monitoring', 'satellite monitoring', 'deforestation monitoring'],
        'C6': ['违规响应', '申诉机制', 'grievance', 'violation response', 'non-compliance', 'corrective action'],
        'C7': ['小农户', 'smallholder', 'small farmer', '农户支持', 'farmer support'],
        'C8': ['认证比例', 'RSPO', 'RTRS', '可持续认证', 'certification', 'certified', 'IP/SG/MB'],
        'C9': ['利益相关方', 'NGO', '多方倡议', 'stakeholder', 'multi-stakeholder', 'NGO engagement'],
        'C10': ['可持续采购报告', 'CDP森林', '进展报告', 'sustainable procurement report', 'CDP forests', 'progress report'],
        
        # 大豆专属DDQ关键词
        'S1': ['巴西大豆', '塞拉多', '亚马逊', '马托格罗索', 'Brazil soy', 'Cerrado', 'Amazon', 'Mato Grosso', 'biome'],
        'S2': ['直接采购', '间接采购', '贸易商', 'direct procurement', 'indirect', 'trader', 'merchant'],
        'S3': ['巴西森林法', 'CAR登记', '环境合规', 'Forest Code', 'CAR registry', 'environmental compliance'],
        'S4': ['塞拉多承诺', 'Cerrado commitment', 'Cerrado protection'],
        'S5': ['四大粮商', 'ADM', 'Bunge', 'Cargill', 'Louis Dreyfus', 'ABCD'],
        'S6': ['亚马逊大豆禁运', 'Soy Moratorium', 'morratoria'],
        'S7': ['大豆玉米轮作', 'double cropping', 'soy-corn rotation'],
        'S8': ['中国大豆', '非转基因', '黑龙江', 'China soy', 'non-GMO'],
        'S9': ['美国大豆', '阿根廷大豆', 'US soy', 'Argentina soy'],
        'S10': ['压榨设施', '榨油厂', 'crushing facility', 'crusher', 'processing plant'],
        'S11': ['转基因', 'GMO', 'genetically modified'],
        'S12': ['土壤健康', '碳排放', 'soil health', 'carbon emission'],
        'S13': ['劳工权益', '童工', '强迫劳动', 'labor rights', 'child labor', 'forced labor'],
        'S14': ['替代蛋白', '大豆减量', 'alternative protein', 'soy reduction'],
        
        # 棕榈油专属DDQ关键词
        'P1': ['棕榈油NDPE', 'palm oil NDPE'],
        'P2': ['榨油厂', 'mill', 'palm oil mill'],
        'P3': ['种植园', 'plantation', 'estate'],
        'P4': ['泥炭地', 'peatland', 'peat'],
        'P5': ['HCV', '高保护价值', 'High Conservation Value'],
        'P6': ['HCS', '高碳储量', 'High Carbon Stock'],
        'P7': ['RSPO', 'MSPO', 'ISPO'],
        'P8': ['供应商评估', 'supplier assessment'],
        'P9': ['申诉', 'grievance'],
        'P10': ['棕榈油衍生品', 'POD', 'palm oil derivative', 'olein', 'stearin', 'PFAD'],
        
        # 咖啡专属DDQ关键词
        'CF1': ['小农户咖啡', 'smallholder coffee', 'coffee farmer'],
        'CF2': ['咖啡认证', 'Rainforest Alliance', 'UTZ', 'Fairtrade', '4C', 'coffee certification'],
        'CF3': ['咖啡溯源', 'coffee traceability', 'origin'],
        'CF4': ['咖啡产区', '哥伦比亚', '巴西咖啡', '埃塞俄比亚', 'Colombia', 'Brazil coffee', 'Ethiopia'],
        'CF5': ['水洗处理', '日晒处理', 'washed', 'natural process'],
        
        # 可可专属DDQ关键词
        'CC1': ['可可小农户', 'cocoa smallholder', 'cocoa farmer'],
        'CC2': ['科特迪瓦', '加纳', 'Côte d\'Ivoire', 'Ivory Coast', 'Ghana'],
        'CC3': ['童工可可', '童工', 'child labor cocoa', 'forced labor cocoa'],
        'CC4': ['可可认证', 'Rainforest Alliance cocoa', 'UTZ cocoa', 'Fairtrade cocoa'],
        'CC5': ['可可溯源', 'cocoa traceability'],
        
        # 橡胶专属DDQ关键词
        'R1': ['橡胶种植园', 'rubber plantation', 'smallholder rubber'],
        'R2': ['泰国橡胶', '印尼橡胶', '越南橡胶', 'Thailand rubber', 'Indonesia rubber', 'Vietnam rubber'],
        'R3': ['土地利用变化', 'land use change rubber', 'forest conversion rubber'],
        'R4': ['橡胶认证', 'rubber certification', 'GPSNR'],
    }
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_type = self.file_path.suffix.lower()
        self.extracted_text = ""
        self.pages = []
        
    def extract(self) -> Tuple[str, List[Dict]]:
        """
        提取文档全文
        返回: (全文文本, 分页信息列表)
        """
        if self.file_type == '.pdf':
            return self._extract_pdf()
        elif self.file_type in ['.docx', '.doc']:
            return self._extract_docx()
        else:
            raise ValueError(f"不支持的文件格式: {self.file_type}")
    
    def _extract_pdf(self) -> Tuple[str, List[Dict]]:
        """从PDF提取文本（使用PyMuPDF）"""
        doc = fitz.open(self.file_path)
        full_text = []
        pages_info = []
        
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            full_text.append(text)
            pages_info.append({
                'page': page_num,
                'text': text,
                'char_count': len(text)
            })
        
        doc.close()
        self.extracted_text = "\n".join(full_text)
        self.pages = pages_info
        return self.extracted_text, pages_info
    
    def _extract_docx(self) -> Tuple[str, List[Dict]]:
        """从Word文档提取文本"""
        doc = docx.Document(self.file_path)
        full_text = []
        pages_info = []
        
        # Word没有明确页码，按段落分组
        for para_num, para in enumerate(doc.paragraphs, 1):
            text = para.text.strip()
            if text:
                full_text.append(text)
                pages_info.append({
                    'page': f"段落{para_num}",
                    'text': text,
                    'char_count': len(text)
                })
        
        self.extracted_text = "\n".join(full_text)
        self.pages = pages_info
        return self.extracted_text, pages_info
    
    def search_ddq_evidence(self, ddq_id: str) -> List[Dict]:
        """
        搜索特定DDQ问题的证据
        返回匹配的证据列表
        """
        keywords = self.DDQ_KEYWORDS.get(ddq_id, [])
        if not keywords:
            return []
        
        evidence_list = []
        
        for page_info in self.pages:
            page_text = page_info['text']
            
            for keyword in keywords:
                # 使用正则表达式进行模糊匹配
                pattern = re.compile(keyword, re.IGNORECASE)
                matches = pattern.finditer(page_text)
                
                for match in matches:
                    # 提取上下文（前后各100字符）
                    start = max(0, match.start() - 100)
                    end = min(len(page_text), match.end() + 100)
                    context = page_text[start:end]
                    
                    # 计算证据等级
                    evidence_tier = self._assess_evidence_tier(context, keyword)
                    
                    evidence_list.append({
                        'ddq_id': ddq_id,
                        'keyword': keyword,
                        'context': context.strip(),
                        'page': page_info['page'],
                        'char_position': match.start(),
                        'evidence_tier': evidence_tier
                    })
        
        # 按证据等级排序（Tier1优先）
        evidence_list.sort(key=lambda x: x['evidence_tier'])
        return evidence_list
    
    def _assess_evidence_tier(self, context: str, keyword: str) -> str:
        """
        评估证据等级
        Tier1: 明确回答问题（含数据/百分比/具体承诺）
        Tier2: 相关信息但未直接回答
        Tier3: 仅提及关键词，无实质内容
        """
        context_lower = context.lower()
        
        # Tier1判定：包含具体数据、百分比、明确承诺
        tier1_patterns = [
            r'\d+%',  # 百分比
            r'\d+\s*(吨|万吨|吨/年)',  # 数量
            r'(承诺|目标|计划).{0,20}(2030|2025|2025|2030)',  # 时间目标
            r'(获得|通过|取得).{0,10}(认证|certificate)',  # 认证
            r'(覆盖|涉及).{0,20}\d+',  # 覆盖范围
        ]
        
        for pattern in tier1_patterns:
            if re.search(pattern, context):
                return 'Tier1'
        
        # Tier2判定：有相关描述但无具体数据
        tier2_keywords = ['政策', '制度', '建立', '实施', '管理', '监测', '评估', 
                         'policy', 'system', 'establish', 'implement', 'manage', 'monitor']
        if any(kw in context_lower for kw in tier2_keywords):
            return 'Tier2'
        
        # 默认Tier3
        return 'Tier3'
    
    def extract_all_ddq(self) -> Dict[str, List[Dict]]:
        """提取所有DDQ问题的证据"""
        results = {}
        for ddq_id in self.DDQ_KEYWORDS.keys():
            evidence = self.search_ddq_evidence(ddq_id)
            if evidence:
                results[ddq_id] = evidence
        return results
    
    def generate_ddq_csv(self, output_path: str):
        """生成DDQ评估表CSV文件"""
        ddq_data = self.extract_all_ddq()
        
        # 加载DDQ问题库
        ddq_questions = self._load_ddq_questions()
        
        rows = []
        for ddq_id in ddq_questions.keys():
            evidence_list = ddq_data.get(ddq_id, [])
            question_info = ddq_questions[ddq_id]
            
            if evidence_list:
                # 取最高等级的证据
                best_evidence = min(evidence_list, key=lambda x: x['evidence_tier'])
                rows.append({
                    'DDQ编号': ddq_id,
                    '问题分类': question_info['category'],
                    '问题原文': question_info['question'],
                    '证据原文': best_evidence['context'][:500],  # 截断至500字符
                    '证据来源文件': self.file_path.name,
                    '页码/段落': f"Page {best_evidence['page']}",
                    '证据等级': best_evidence['evidence_tier'],
                    '回答状态': '已回答' if best_evidence['evidence_tier'] == 'Tier1' else '部分回答',
                    '审核状态': '待审核',
                    '审核备注': ''
                })
            else:
                # 无证据
                rows.append({
                    'DDQ编号': ddq_id,
                    '问题分类': question_info['category'],
                    '问题原文': question_info['question'],
                    '证据原文': '',
                    '证据来源文件': '',
                    '页码/段落': '',
                    '证据等级': 'Tier3',
                    '回答状态': '未找到',
                    '审核状态': '待审核',
                    '审核备注': ''
                })
        
        # 写入CSV
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        return output_path
    
    def _load_ddq_questions(self) -> Dict:
        """加载DDQ问题库（简化版）"""
        # 这里应该读取 references/ddq-questions.md
        # 简化示例
        return {
            'C1': {'category': '企业概况与承诺', 'question': '企业是否有公开的无毁林、无泥炭地、无剥削（NDPE）或同等级别的可持续采购承诺？'},
            'C2': {'category': '供应链透明度', 'question': '企业是否披露了主要供应商名单及地理位置信息？'},
            # ... 更多问题
        }


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='从PDF/Word报告中提取DDQ证据')
    parser.add_argument('input', help='输入文件路径(PDF或Word)')
    parser.add_argument('-o', '--output', default='ddq_assessment.csv', help='输出CSV文件路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细输出')
    
    args = parser.parse_args()
    
    print(f"🔍 正在提取证据: {args.input}")
    
    extractor = EvidenceExtractor(args.input)
    
    # 提取文本
    text, pages = extractor.extract()
    print(f"📄 已提取 {len(pages)} 页/段落，共 {len(text)} 字符")
    
    # 生成DDQ评估表
    output_path = extractor.generate_ddq_csv(args.output)
    print(f"✅ DDQ评估表已生成: {output_path}")
    
    if args.verbose:
        # 显示统计
        ddq_data = extractor.extract_all_ddq()
        print(f"\n📊 证据统计:")
        for ddq_id, evidence_list in ddq_data.items():
            tier1 = len([e for e in evidence_list if e['evidence_tier'] == 'Tier1'])
            tier2 = len([e for e in evidence_list if e['evidence_tier'] == 'Tier2'])
            print(f"  {ddq_id}: {len(evidence_list)}条证据 (Tier1:{tier1}, Tier2:{tier2})")


if __name__ == '__main__':
    main()
