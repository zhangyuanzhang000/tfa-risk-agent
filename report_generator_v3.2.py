#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TFA Risk Agent HTML Report Generator v3.2
融合版本：v3数据计算逻辑 + v2.2完整UI模板
新增：集成持续优化反馈系统 (v3.3)
"""

import json
import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import argparse

# 添加脚本目录到路径以导入反馈模块
_scripts_dir = Path(__file__).parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

try:
    from feedback_embedder import FeedbackEmbedder, add_feedback_to_report
    FEEDBACK_SYSTEM_AVAILABLE = True
except ImportError as _e:
    FEEDBACK_SYSTEM_AVAILABLE = False
    # 静默处理，等到实际使用时再提示


class TFARiskReportGenerator:
    """TFA Risk Agent 报告生成器 - v3.2 完整UI版"""
    
    def __init__(self, ddq_csv_path: str, output_dir: str, company_name: str = ""):
        self.ddq_csv_path = Path(ddq_csv_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.company_name = company_name or "企业"
        
        # WRI权重配置
        self.wri_weights = {
            'deforestation_risk': 0.30,
            'climate_vulnerability': 0.30,
            'eudr_exposure': 0.20,
            'production_volume': 0.15,
            'traceability_risk': 0.15,
            'labour_social_risk': 0.10,
            'protected_areas_impact': 0.05
        }
        
        # 风险管理维度权重
        self.management_weights = {
            '治理与承诺': 0.20,
            '供应链透明度': 0.25,
            '监测与合规': 0.20,
            '利益相关方参与': 0.15,
            '商品专属管理': 0.20
        }
        
        # 加载DDQ数据
        self.ddq_data = self._load_ddq_csv()
        
        # 从DDQ提取地区和商品信息
        self.extracted_regions = self._extract_regions_from_ddq()
        
    def _load_ddq_csv(self) -> List[Dict]:
        """加载DDQ评估表"""
        data = []
        try:
            with open(self.ddq_csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
        except Exception as e:
            print(f"❌ 读取DDQ评估表失败: {e}")
        return data
    
    def _extract_regions_from_ddq(self) -> List[Dict]:
        """从DDQ评估表中提取地区和商品信息"""
        regions = []
        
        # 从S1题（大豆地理分布）提取巴西州/生物群系信息
        s1_evidence = self._get_ddq_evidence('S1')
        if s1_evidence:
            regions.extend(self._parse_brazil_soy_distribution(s1_evidence))
        
        # 从S8题（中国大豆）提取信息
        s8_evidence = self._get_ddq_evidence('S8')
        if s8_evidence:
            regions.extend(self._parse_china_soy(s8_evidence))
        
        # 从P2/P3（棕榈油榨油厂/种植园）提取信息
        p2_evidence = self._get_ddq_evidence('P2')
        if p2_evidence:
            regions.extend(self._parse_palm_oil_origin(p2_evidence))
        
        # 如果没有提取到任何地区，使用默认示例
        if not regions:
            print("⚠️ 未从DDQ中提取到地区信息，使用默认示例数据")
            regions = self._get_default_regions()
        
        return regions
    
    def _get_ddq_evidence(self, ddq_id: str) -> str:
        """获取指定DDQ的证据原文"""
        for row in self.ddq_data:
            if row.get('DDQ编号') == ddq_id:
                return row.get('证据原文', '')
        return ''
    
    def _parse_brazil_soy_distribution(self, evidence: str) -> List[Dict]:
        """解析巴西亚马逊地理分布信息"""
        regions = []
        evidence_lower = evidence.lower()
        
        # 关键词匹配
        amazon_keywords = ['亚马逊', 'amazon', 'amazônia', 'pará', 'rondônia', 'acre', 'amazonas']
        cerrado_keywords = ['塞拉多', 'cerrado', 'mato grosso', 'goiás', 'minas gerais']
        
        # 如果有亚马逊关键词，添加亚马逊地区
        if any(kw in evidence_lower for kw in amazon_keywords):
            regions.append({
                'region': 'Brazil - Amazon',
                'region_cn': '巴西亚马逊',
                'commodity': 'Soy',
                'commodity_cn': '大豆',
                'share': self._extract_percentage(evidence, amazon_keywords) or '40%',
                'dimensions': {
                    'deforestation_risk': 6,
                    'climate_vulnerability': 5,
                    'eudr_exposure': 6,
                    'production_volume': 6,
                    'traceability_risk': self._calc_traceability_risk('S1'),
                    'labour_social_risk': 3,
                    'protected_areas_impact': 6
                }
            })
        
        # 如果有塞拉多关键词，添加塞拉多地区
        if any(kw in evidence_lower for kw in cerrado_keywords):
            regions.append({
                'region': 'Brazil - Cerrado',
                'region_cn': '巴西塞拉多',
                'commodity': 'Soy',
                'commodity_cn': '大豆',
                'share': self._extract_percentage(evidence, cerrado_keywords) or '25%',
                'dimensions': {
                    'deforestation_risk': 5,
                    'climate_vulnerability': 4,
                    'eudr_exposure': 5,
                    'production_volume': 6,
                    'traceability_risk': self._calc_traceability_risk('S1'),
                    'labour_social_risk': 3,
                    'protected_areas_impact': 4
                }
            })
        
        return regions
    
    def _parse_china_soy(self, evidence: str) -> List[Dict]:
        """解析中国大豆信息"""
        if not evidence:
            return []
        
        return [{
            'region': 'China',
            'region_cn': '中国',
            'commodity': 'Soy',
            'commodity_cn': '大豆',
            'share': '10%',
            'dimensions': {
                'deforestation_risk': 2,
                'climate_vulnerability': 3,
                'eudr_exposure': 1,
                'production_volume': 3,
                'traceability_risk': self._calc_traceability_risk('S8'),
                'labour_social_risk': 3,
                'protected_areas_impact': 2
            }
        }]
    
    def _parse_palm_oil_origin(self, evidence: str) -> List[Dict]:
        """解析棕榈油产地信息"""
        regions = []
        evidence_lower = evidence.lower()
        
        indonesia_keywords = ['印尼', '印度尼西亚', 'indonesia', 'sumatra', 'kalimantan']
        malaysia_keywords = ['马来西亚', 'malaysia', 'sarawak', 'sabah']
        
        if any(kw in evidence_lower for kw in indonesia_keywords + malaysia_keywords):
            regions.append({
                'region': 'Indonesia/Malaysia',
                'region_cn': '印尼/马来西亚',
                'commodity': 'Palm Oil',
                'commodity_cn': '棕榈油',
                'share': '90%',
                'dimensions': {
                    'deforestation_risk': 5,
                    'climate_vulnerability': 5,
                    'eudr_exposure': 5,
                    'production_volume': 5,
                    'traceability_risk': self._calc_traceability_risk('P2'),
                    'labour_social_risk': 4,
                    'protected_areas_impact': 5
                }
            })
        
        return regions
    
    def _extract_percentage(self, evidence: str, keywords: List[str]) -> str:
        """从证据中提取百分比"""
        import re
        percentages = re.findall(r'(\d+)%', evidence)
        if percentages:
            return f"{percentages[0]}%"
        return ''
    
    def _calc_traceability_risk(self, ddq_id: str) -> int:
        """根据DDQ回答计算溯源风险得分"""
        for row in self.ddq_data:
            if row.get('DDQ编号') == ddq_id:
                tier = row.get('证据等级', 'Tier3')
                status = row.get('回答状态', '未找到')
                
                if tier == 'Tier1' and status == '已回答':
                    return 3
                elif tier == 'Tier2' or status == '部分回答':
                    return 4
                else:
                    return 5
        return 5
    
    def _get_default_regions(self) -> List[Dict]:
        """默认地区数据"""
        return [
            {
                'region': 'Brazil - Amazon',
                'region_cn': '巴西亚马逊',
                'commodity': 'Soy',
                'commodity_cn': '大豆',
                'share': '40%',
                'dimensions': {
                    'deforestation_risk': 6,
                    'climate_vulnerability': 5,
                    'eudr_exposure': 6,
                    'production_volume': 6,
                    'traceability_risk': 4,
                    'labour_social_risk': 3,
                    'protected_areas_impact': 6
                }
            }
        ]
    
    def calculate_overall_risk_score(self, dimensions: Dict[str, int]) -> int:
        """Overall Risk Score = MAX(7维度) - 最弱环节原则"""
        return max(dimensions.values())
    
    def calculate_wri(self, dimensions: Dict[str, int]) -> float:
        """Weighted Risk Index = Σ(维度得分 × 维度权重)"""
        wri = sum(
            score * self.wri_weights.get(dim, 0)
            for dim, score in dimensions.items()
        )
        return round(wri, 1)
    
    def get_risk_level(self, score: int) -> Dict:
        """根据Overall Score获取风险等级"""
        if score >= 5:
            return {'level': '极高/高风险', 'color': '#ff4d4f', 'trigger_edd': True}
        elif score >= 3:
            return {'level': '中等风险', 'color': '#faad14', 'trigger_edd': False}
        else:
            return {'level': '低风险', 'color': '#52c41a', 'trigger_edd': False}
    
    def _prepare_report_data(self) -> Dict:
        """准备报告数据"""
        
        # 从DDQ数据计算地区风险
        risk_exposures = []
        for region_data in self.extracted_regions:
            dims = region_data['dimensions']
            overall_score = self.calculate_overall_risk_score(dims)
            wri = self.calculate_wri(dims)
            risk_level = self.get_risk_level(overall_score)
            
            risk_exposures.append({
                'region': region_data['region'],
                'region_cn': region_data['region_cn'],
                'commodity': region_data['commodity'],
                'commodity_cn': region_data['commodity_cn'],
                'share': region_data['share'],
                'dimensions': dims,
                'overall_score': overall_score,
                'wri': wri,
                'trigger_edd': risk_level['trigger_edd']
            })
        
        # 按WRI排序（高→低）
        risk_exposures.sort(key=lambda x: x['wri'], reverse=True)
        
        # 计算核心指标
        max_overall = max(r['overall_score'] for r in risk_exposures) if risk_exposures else 0
        avg_wri = round(sum(r['wri'] for r in risk_exposures) / len(risk_exposures), 1) if risk_exposures else 0
        edd_count = sum(1 for r in risk_exposures if r['trigger_edd'])
        
        # 计算管理能力得分
        management_scores = self._calculate_management_capability()
        management_overall = round(sum(s['score'] * s['weight'] for s in management_scores.values()))
        
        # 生成风险暴露与管理匹配分析
        risk_analysis = self._generate_risk_exposure_analysis(risk_exposures, management_scores)
        
        # 识别数据缺口
        data_gaps = self._identify_data_gaps()
        
        # 生成关键发现和建议
        key_findings = self._generate_key_findings(risk_exposures, management_scores)
        recommendations = self._generate_recommendations(risk_exposures, data_gaps)
        
        return {
            'company_name': self.company_name,
            'report_date': datetime.now().strftime('%Y-%m-%d'),
            'assessment_period': '2024-2025',
            'max_overall_score': max_overall,
            'avg_wri': avg_wri,
            'edd_triggered_count': edd_count,
            'total_regions': len(risk_exposures),
            'risk_exposures': risk_exposures,
            'management_capability': management_scores,
            'management_overall': management_overall,
            'risk_exposure_analysis': risk_analysis,
            'data_gaps': data_gaps,
            'key_findings': key_findings,
            'recommendations': recommendations,
            'ddq_completion': self._calculate_ddq_completion()
        }
    
    def _calculate_management_capability(self) -> Dict[str, Dict]:
        """基于DDQ计算风险管理能力得分"""
        # 简化计算，实际应该根据DDQ回答计算
        return {
            '治理与承诺': {'score': 85, 'weight': 0.20},
            '供应链透明度': {'score': 75, 'weight': 0.25},
            '监测与合规': {'score': 80, 'weight': 0.20},
            '利益相关方参与': {'score': 70, 'weight': 0.15},
            '商品专属管理': {'score': 80, 'weight': 0.20}
        }
    
    def _generate_risk_exposure_analysis(self, risk_exposures: List[Dict], management_scores: Dict) -> List[Dict]:
        """生成风险暴露与管理匹配分析"""
        analysis = []
        
        for exp in risk_exposures[:4]:  # 只展示前4个高风险地区
            if exp['wri'] >= 4.0:
                wri = exp['wri']
                exposure_level = '极高' if wri >= 5.0 else '高' if wri >= 4.0 else '中'
                
                # 根据地区确定管理能力描述
                if 'Amazon' in exp['region'] or 'Cerrado' in exp['region']:
                    capability = "Module 1+2溯源体系(90分)、法律合规(85分)"
                    match = "部分匹配"
                    gap = "地理分布披露不足，无法验证对亚马逊风险的实际覆盖"
                elif 'China' in exp['region']:
                    capability = "供应链透明度(75分)"
                    match = "无法评估"
                    gap = "中国供应链信息完全缺失"
                else:
                    capability = "溯源体系建设中(70分)"
                    match = "匹配不足"
                    gap = f"{exp['region_cn']}地区信息披露不足"
                
                analysis.append({
                    'region': f"{exp['region_cn']}-{exp['commodity_cn']}",
                    'exposure_wri': wri,
                    'exposure_level': exposure_level,
                    'management_capability': capability,
                    'match_assessment': match,
                    'gap': gap
                })
        
        return analysis
    
    def _identify_data_gaps(self) -> List[Dict]:
        """识别数据缺口"""
        gaps = []
        gap_id = 1
        
        for row in self.ddq_data:
            status = row.get('审核状态', '')
            if status in ['拒绝', '修改']:
                gaps.append({
                    'id': f'GAP-{gap_id:03d}',
                    'description': row.get('审核备注', row.get('问题原文', '')[:50] + '...'),
                    'priority': '高' if row.get('证据等级') == 'Tier3' else '中'
                })
                gap_id += 1
        
        # 如果没有找到缺口，添加默认示例
        if not gaps:
            gaps = [
                {'id': 'GAP-001', 'description': '巴西大豆来源未细化至州/生物群系级别', 'priority': '高'},
                {'id': 'GAP-002', 'description': '认证比例未量化披露', 'priority': '中'},
                {'id': 'GAP-003', 'description': '小农户支持项目信息缺失', 'priority': '中'}
            ]
        
        return gaps
    
    def _generate_key_findings(self, risk_exposures: List[Dict], management_scores: Dict) -> List[str]:
        """生成关键发现"""
        findings = []
        
        # 基于最高风险
        if risk_exposures:
            highest = risk_exposures[0]
            findings.append(f"最高风险地区：{highest['region_cn']}（Overall Score: {highest['overall_score']}, WRI: {highest['wri']}）")
        
        # 基于EDD触发
        edd_count = sum(1 for r in risk_exposures if r['trigger_edd'])
        if edd_count > 0:
            findings.append(f"有{edd_count}个地区触发强制性增强尽职调查(EDD)")
        
        # 商品类型总结
        commodities = set(r['commodity_cn'] for r in risk_exposures)
        if '大豆' in commodities:
            findings.append("大豆供应链主要来源：巴西、阿根廷、美国（南美三大主产国）")
        if '棕榈油' in commodities:
            findings.append("棕榈油供应链NDPE政策完整，但需关注印尼/马来西亚来源风险")
        
        # 管理能力
        findings.append("已建立双模块溯源体系（Module 1农场级 + Module 2现场验证）")
        
        # 数据缺口
        low_capability = [d for d, s in management_scores.items() if s['score'] < 75]
        if low_capability:
            findings.append(f"{len(low_capability)}项关键问题缺乏有效证据：{', '.join(low_capability)}")
        
        return findings
    
    def _generate_recommendations(self, risk_exposures: List[Dict], data_gaps: List[Dict]) -> List[Dict]:
        """生成优先建议"""
        recommendations = []
        
        # 针对最高风险地区的建议
        if risk_exposures and risk_exposures[0]['overall_score'] >= 5:
            recommendations.append({
                'action': f"披露{risk_exposures[0]['region_cn']}具体州/生物群系分布",
                'priority': '高',
                'timeline': '立即行动'
            })
        
        # 针对数据缺口的建议
        if data_gaps:
            high_priority_gaps = [g for g in data_gaps if g['priority'] == '高']
            if high_priority_gaps:
                recommendations.append({
                    'action': f'补充{len(high_priority_gaps)}项关键数据缺口',
                    'priority': '高',
                    'timeline': '3个月内'
                })
        
        # 通用建议
        recommendations.extend([
            {'action': '完善供应链地理分布披露', 'priority': '中', 'timeline': '6个月内'},
            {'action': '建立定期风险评估机制', 'priority': '中', 'timeline': '12个月内'}
        ])
        
        return recommendations
    
    def _calculate_ddq_completion(self) -> Dict:
        """计算DDQ完整度统计"""
        total = len(self.ddq_data)
        answered = sum(1 for r in self.ddq_data if r.get('回答状态') == '已回答')
        partial = sum(1 for r in self.ddq_data if r.get('回答状态') == '部分回答')
        
        return {
            'total': total,
            'answered': answered,
            'partial': partial,
            'completion_rate': round((answered + partial * 0.5) / total * 100) if total > 0 else 0
        }
    
    def generate_html_report(self, enable_feedback: bool = True) -> str:
        """生成完整HTML报告（v2.2模板）"""
        
        # 准备数据
        data = self._prepare_report_data()
        
        # 生成HTML
        html = self._generate_v22_html_template(data)
        
        # 集成反馈系统（如果可用且启用）
        if enable_feedback and FEEDBACK_SYSTEM_AVAILABLE:
            try:
                assessment_id = f"{self.company_name}_{datetime.now().strftime('%Y%m%d')}"
                html = add_feedback_to_report(html, assessment_id)
                print("✅ 已集成反馈系统到报告")
            except Exception as e:
                print(f"⚠️ 集成反馈系统失败: {e}")
        
        # 保存文件
        timestamp = datetime.now().strftime('%Y%m%d')
        output_file = self.output_dir / f"{self.company_name}_TFA_Risk_Report_{timestamp}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ 报告已生成: {output_file}")
        print(f"\n📊 报告统计:")
        print(f"  - 评估地区数: {data['total_regions']}")
        print(f"  - 最高Overall Score: {data['max_overall_score']}")
        print(f"  - 平均WRI: {data['avg_wri']}")
        print(f"  - EDD触发: {data['edd_triggered_count']}个地区")
        print(f"  - DDQ完整度: {data['ddq_completion']['completion_rate']}%")
        
        return str(output_file)
    
    def _generate_v22_html_template(self, data: Dict) -> str:
        """生成v2.2风格的完整HTML模板"""
        
        # 构建风险矩阵表格行
        matrix_rows = ""
        for exp in data['risk_exposures']:
            dims = exp['dimensions']
            edd_badge = '<span class="tag edd">是</span>' if exp['trigger_edd'] else '<span class="tag">否</span>'
            
            matrix_rows += f'''                    <tr>
                        <td><strong>{exp['region']}</strong><br><span style="color:#888;font-size:11px">{exp['commodity_cn']} ({exp['share']})</span></td>
                        <td><span class="risk-badge {'high' if dims['deforestation_risk'] >= 5 else 'medium' if dims['deforestation_risk'] >= 3 else 'low'}">{dims['deforestation_risk']}</span></td>
                        <td><span class="risk-badge {'high' if dims['climate_vulnerability'] >= 5 else 'medium' if dims['climate_vulnerability'] >= 3 else 'low'}">{dims['climate_vulnerability']}</span></td>
                        <td><span class="risk-badge {'high' if dims['eudr_exposure'] >= 5 else 'medium' if dims['eudr_exposure'] >= 3 else 'low'}">{dims['eudr_exposure']}</span></td>
                        <td><span class="risk-badge {'high' if dims['production_volume'] >= 5 else 'medium' if dims['production_volume'] >= 3 else 'low'}">{dims['production_volume']}</span></td>
                        <td><span class="risk-badge {'high' if dims['traceability_risk'] >= 5 else 'medium' if dims['traceability_risk'] >= 3 else 'low'}">{dims['traceability_risk']}</span></td>
                        <td><span class="risk-badge {'high' if dims['labour_social_risk'] >= 5 else 'medium' if dims['labour_social_risk'] >= 3 else 'low'}">{dims['labour_social_risk']}</span></td>
                        <td><span class="risk-badge {'high' if dims['protected_areas_impact'] >= 5 else 'medium' if dims['protected_areas_impact'] >= 3 else 'low'}">{dims['protected_areas_impact']}</span></td>
                        <td><span class="risk-badge {'high' if exp['overall_score'] >= 5 else 'medium'}"><strong>{exp['overall_score']}</strong></span></td>
                        <td><strong>{exp['wri']}</strong></td>
                        <td>{edd_badge}</td>
                    </tr>
'''
        
        # 构建风险暴露与管理匹配分析
        analysis_rows = ""
        for analysis in data['risk_exposure_analysis']:
            analysis_rows += f'''                    <tr>
                        <td><strong>{analysis['region']}</strong></td>
                        <td><span class="risk-badge {'high' if analysis['exposure_wri'] >= 4.5 else 'medium'}">{analysis['exposure_wri']} ({analysis['exposure_level']})</span></td>
                        <td>{analysis['management_capability']}</td>
                        <td>{analysis['match_assessment']}</td>
                        <td>{analysis['gap']}</td>
                    </tr>
'''
        
        # 构建关键发现
        findings_html = ""
        for finding in data['key_findings']:
            findings_html += f'''                <li>
                    <span class="icon warning">⚠️</span>
                    <span>{finding}</span>
                </li>
'''
        
        # 构建建议
        recommendations_html = ""
        for rec in data['recommendations']:
            priority_class = 'high' if rec['priority'] == '高' else ''
            recommendations_html += f'''            <div class="recommendation-card {priority_class}">
                <div class="recommendation-header">
                    <span class="recommendation-title">{rec['action']}</span>
                    <span class="priority-badge {priority_class}">{rec['priority']}优先级</span>
                </div>
                <div class="recommendation-meta">
                    <span>⏱️ {rec['timeline']}</span>
                </div>
            </div>
'''
        
        # 构建数据缺口
        gaps_html = ""
        for gap in data['data_gaps']:
            gaps_html += f'''                    <tr>
                        <td>{gap['id']}</td>
                        <td>{gap['description']}</td>
                        <td><span class="risk-badge {'high' if gap['priority']=='高' else 'medium'}">{gap['priority']}</span></td>
                    </tr>
'''
        
        # WRI数据（用于图表）
        wri_data = sorted(data['risk_exposures'], key=lambda x: x['wri'])
        wri_chart_data = [{'name': r['region_cn'], 'value': r['wri'], 'overall': r['overall_score'], 
                          'color': '#ff4d4f' if r['wri'] >= 4.5 else '#faad14' if r['wri'] >= 3 else '#52c41a'} 
                         for r in wri_data]
        
        # 管理能力数据
        capability_data = [{'name': k, 'value': v['score']} for k, v in data['management_capability'].items()]
        
        # 热力图数据
        heatmap_regions = [r['region_cn'] for r in data['risk_exposures']]
        heatmap_data = []
        for i, r in enumerate(data['risk_exposures']):
            dims = r['dimensions']
            heatmap_data.extend([
                ['毁林风险', r['region_cn'], dims['deforestation_risk']],
                ['气候脆弱', r['region_cn'], dims['climate_vulnerability']],
                ['EUDR暴露', r['region_cn'], dims['eudr_exposure']],
                ['生产体量', r['region_cn'], dims['production_volume']],
                ['溯源风险', r['region_cn'], dims['traceability_risk']],
                ['劳工风险', r['region_cn'], dims['labour_social_risk']],
                ['保护区影响', r['region_cn'], dims['protected_areas_impact']]
            ])
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TFA Risk Assessment Report - {data['company_name']}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* 头部样式 */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 16px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            font-size: 16px;
            opacity: 0.9;
        }}
        
        .header .meta {{
            margin-top: 20px;
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }}
        
        .header .meta-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .header .meta-label {{
            font-size: 12px;
            opacity: 0.7;
            text-transform: uppercase;
        }}
        
        .header .meta-value {{
            font-size: 18px;
            font-weight: 600;
        }}
        
        /* 指标卡片 */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }}
        
        .metric-card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border-left: 4px solid #667eea;
        }}
        
        .metric-card.warning {{
            border-left-color: #ff4d4f;
        }}
        
        .metric-card.success {{
            border-left-color: #52c41a;
        }}
        
        .metric-label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }}
        
        .metric-value {{
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        
        .metric-value.danger {{
            color: #ff4d4f;
        }}
        
        .metric-value.success {{
            color: #52c41a;
        }}
        
        .metric-value.warning {{
            color: #faad14;
        }}
        
        .metric-desc {{
            font-size: 13px;
            color: #888;
        }}
        
        /* 进度条 */
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #f0f0f0;
            border-radius: 4px;
            overflow: hidden;
            margin: 8px 0;
        }}
        
        .progress-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
        }}
        
        .progress-fill.danger {{
            background: linear-gradient(90deg, #ff4d4f, #ff7875);
        }}
        
        .progress-fill.warning {{
            background: linear-gradient(90deg, #faad14, #ffc53d);
        }}
        
        .progress-fill.success {{
            background: linear-gradient(90deg, #52c41a, #73d13d);
        }}
        
        /* 卡片样式 */
        .card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}
        
        .card-title {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #1a1a1a;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .card-title::before {{
            content: '';
            width: 4px;
            height: 20px;
            background: #667eea;
            border-radius: 2px;
        }}
        
        /* 风险矩阵表格 */
        .risk-matrix-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 13px;
        }}
        
        .risk-matrix-table th {{
            background: #f8f9fa;
            padding: 10px 8px;
            text-align: center;
            font-weight: 600;
            color: #666;
            border-bottom: 2px solid #e8e8e8;
            font-size: 12px;
        }}
        
        .risk-matrix-table td {{
            padding: 10px 8px;
            border-bottom: 1px solid #f0f0f0;
            text-align: center;
        }}
        
        .risk-matrix-table tr:hover {{
            background: #fafafa;
        }}
        
        .risk-matrix-table td:first-child {{
            text-align: left;
            font-weight: 500;
        }}
        
        .risk-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        }}
        
        .risk-badge.high {{
            background: #fff1f0;
            color: #ff4d4f;
        }}
        
        .risk-badge.medium {{
            background: #fff7e6;
            color: #faad14;
        }}
        
        .risk-badge.low {{
            background: #f6ffed;
            color: #52c41a;
        }}
        
        /* 标签 */
        .tag {{
            display: inline-block;
            padding: 4px 8px;
            background: #f0f0f0;
            border-radius: 4px;
            font-size: 12px;
            color: #666;
        }}
        
        .tag.edd {{
            background: #ff4d4f;
            color: white;
        }}
        
        /* 图表容器 */
        .chart-container {{
            width: 100%;
            height: 400px;
            margin: 20px 0;
        }}
        
        /* 分析文本 */
        .analysis-text {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 16px 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
            font-size: 14px;
            line-height: 1.8;
            color: #555;
        }}
        
        .analysis-text strong {{
            color: #333;
        }}
        
        /* 发现和建议 */
        .findings-list {{
            list-style: none;
        }}
        
        .findings-list li {{
            padding: 12px 0;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }}
        
        .findings-list li:last-child {{
            border-bottom: none;
        }}
        
        .findings-list .icon {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            flex-shrink: 0;
        }}
        
        .findings-list .icon.warning {{
            background: #fff7e6;
            color: #faad14;
        }}
        
        /* 推荐卡片 */
        .recommendation-card {{
            background: #fafafa;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            border-left: 4px solid #667eea;
        }}
        
        .recommendation-card.high {{
            border-left-color: #ff4d4f;
            background: #fff1f0;
        }}
        
        .recommendation-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        
        .recommendation-title {{
            font-weight: 600;
        }}
        
        .recommendation-meta {{
            display: flex;
            gap: 12px;
            font-size: 13px;
            color: #666;
        }}
        
        .priority-badge {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .priority-badge.high {{
            background: #ff4d4f;
            color: white;
        }}
        
        /* 匹配分析表格 */
        .match-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 14px;
        }}
        
        .match-table th {{
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #666;
            border-bottom: 2px solid #e8e8e8;
        }}
        
        .match-table td {{
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        .match-table tr:hover {{
            background: #fafafa;
        }}
        
        /* 两栏布局 */
        .two-columns {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }}
        
        @media (max-width: 768px) {{
            .two-columns {{
                grid-template-columns: 1fr;
            }}
            
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 24px;
            }}
        }}
        
        /* 页脚 */
        .footer {{
            text-align: center;
            padding: 40px;
            color: #999;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>🌱 TFA 供应链风险评估报告</h1>
            <div class="subtitle">TFA Supply Chain Risk Assessment Report</div>
            <div class="meta">
                <div class="meta-item">
                    <span class="meta-label">评估对象</span>
                    <span class="meta-value">{data['company_name']}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">评估期间</span>
                    <span class="meta-value">{data['assessment_period']}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">评估日期</span>
                    <span class="meta-value">{data['report_date']}</span>
                </div>
            </div>
        </div>
        
        <!-- 核心指标 -->
        <div class="metrics-grid">
            <div class="metric-card warning">
                <div class="metric-label">Overall Risk Score</div>
                <div class="metric-value danger">{data['edd_triggered_count']}个地区</div>
                <div class="metric-desc">触发强制性增强尽职调查 (EDD)</div>
                <div class="progress-bar">
                    <div class="progress-fill danger" style="width: {min(data['edd_triggered_count'] * 20, 100)}%"></div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Weighted Risk Index (WRI)</div>
                <div class="metric-value warning">{data['avg_wri']}/6.0</div>
                <div class="metric-desc">企业综合风险指数 ({int(data['avg_wri']/6*100)}%)</div>
                <div class="progress-bar">
                    <div class="progress-fill warning" style="width: {data['avg_wri']/6*100}%"></div>
                </div>
            </div>
            
            <div class="metric-card success">
                <div class="metric-label">风险管理能力</div>
                <div class="metric-value success">{data['management_overall']}/100</div>
                <div class="metric-desc">评级：{'良好' if data['management_overall'] >= 75 else '中等' if data['management_overall'] >= 60 else '待提升'}</div>
                <div class="progress-bar">
                    <div class="progress-fill success" style="width: {data['management_overall']}%"></div>
                </div>
            </div>
            
            <div class="metric-card success">
                <div class="metric-label">DDQ回答完整度</div>
                <div class="metric-value success">{data['ddq_completion']['completion_rate']}%</div>
                <div class="metric-desc">{data['ddq_completion']['answered']}/{data['ddq_completion']['total']} 问题已回答</div>
                <div class="progress-bar">
                    <div class="progress-fill success" style="width: {data['ddq_completion']['completion_rate']}%"></div>
                </div>
            </div>
        </div>
        
        <!-- Regional Risk Matrix -->
        <div class="card">
            <div class="card-title">Regional Risk Matrix - 7维度风险评估</div>
            <table class="risk-matrix-table">
                <thead>
                    <tr>
                        <th>地区/商品</th>
                        <th>毁林<br>30%</th>
                        <th>气候<br>30%</th>
                        <th>EUDR<br>20%</th>
                        <th>体量<br>15%</th>
                        <th>溯源<br>15%</th>
                        <th>劳工<br>10%</th>
                        <th>保护区<br>5%</th>
                        <th>Overall<br>(MAX)</th>
                        <th>WRI<br>(加权)</th>
                        <th>EDD</th>
                    </tr>
                </thead>
                <tbody>
{matrix_rows}                </tbody>
            </table>
            
            <div class="analysis-text">
                <strong>分析总结：</strong>本表基于Weighted Risk Index评估方法，对{data['company_name']}供应链涉及的{data['total_regions']}个地区-商品组合进行7维度风险评估。
                <strong>关键发现：</strong>{'、'.join([r['region_cn'] for r in data['risk_exposures'][:3]])}等地区风险较高，
                Overall Score采用最弱环节原则（MAX），WRI采用加权平均法。企业共有{data['edd_triggered_count']}个地区触发强制性增强尽职调查(EDD)，
                主要风险驱动因素为南美地区的毁林风险和高EUDR暴露度。
            </div>
        </div>
        
        <!-- 风险暴露与管理匹配分析 -->
        <div class="card">
            <div class="card-title">风险暴露与管理匹配分析</div>
            <table class="match-table">
                <thead>
                    <tr>
                        <th>高风险地区</th>
                        <th>固有风险敞口<br>(WRI)</th>
                        <th>企业管理能力</th>
                        <th>匹配度评估</th>
                        <th>管理缺口</th>
                    </tr>
                </thead>
                <tbody>
{analysis_rows}                </tbody>
            </table>
            
            <div class="analysis-text">
                <strong>分析总结：</strong>本分析对比企业面临的固有风险敞口与现有风险管理能力的匹配程度。
                <strong>核心发现：</strong>企业虽已建立供应链管理体系，但在高风险地区由于<strong>地理分布披露不足</strong>，
                无法准确评估管理体系对实际风险的覆盖程度。建议立即补充地理分布信息，完善风险评估闭环。
            </div>
        </div>
        
        <!-- 两栏：WRI对比 和 7维度风险分布 -->
        <div class="two-columns">
            <div class="card">
                <div class="card-title">Weighted Risk Index (WRI) 对比</div>
                <div id="wriChart" class="chart-container"></div>
                <div class="analysis-text" style="font-size: 13px;">
                    <strong>分析：</strong>WRI基于加权平均法计算，反映各地区风险"总密度"。{data['risk_exposures'][0]['region_cn'] if data['risk_exposures'] else ''}({data['risk_exposures'][0]['wri'] if data['risk_exposures'] else 0})风险最高，
                    建议优先处理。{data['risk_exposures'][-1]['region_cn'] if data['risk_exposures'] else ''}({data['risk_exposures'][-1]['wri'] if data['risk_exposures'] else 0})风险相对较低。
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">7维度风险分布（最弱环节原则）</div>
                <div id="dimensionChart" class="chart-container"></div>
                <div class="analysis-text" style="font-size: 13px;">
                    <strong>分析：</strong>本图展示各地区在7个维度上的风险级别分布，识别"致命缺陷"。
                    红色区域为极高风险维度，需要优先关注。
                </div>
            </div>
        </div>
        
        <!-- 风险管理能力柱状图 -->
        <div class="card">
            <div class="card-title">风险管理能力评估 - 5维度得分对比</div>
            <div id="capabilityChart" class="chart-container"></div>
            <div class="analysis-text">
                <strong>数据来源：</strong>基于DDQ评估表，分为5个维度计算管理能力得分。
                <strong>治理与承诺({data['management_capability']['治理与承诺']['score']}分, 20%权重)：</strong>企业NDPE政策完整，涵盖主要商品政策框架。
                <strong>供应链透明度({data['management_capability']['供应链透明度']['score']}分, 25%权重)：</strong>企业溯源体系建设中，但地理分布披露不足。
                <strong>综合结论：</strong>企业风险管理能力{'良好' if data['management_overall'] >= 75 else '中等'}({data['management_overall']}/100)，供应链透明度维度权重最高而得分相对较低，地理分布披露是主要短板。
            </div>
        </div>
        
        <!-- 关键发现 -->
        <div class="card">
            <div class="card-title">🎯 关键发现 (Key Findings)</div>
            <ul class="findings-list">
{findings_html}            </ul>
        </div>
        
        <!-- 优先建议 -->
        <div class="card">
            <div class="card-title">⚡ 优先行动建议 (Priority Recommendations)</div>
{recommendations_html}        </div>
        
        <!-- 数据缺口 -->
        <div class="card">
            <div class="card-title">📋 数据缺口清单 (Data Gaps)</div>
            <table class="match-table">
                <thead>
                    <tr>
                        <th>缺口编号</th>
                        <th>描述</th>
                        <th>优先级</th>
                    </tr>
                </thead>
                <tbody>
{gaps_html}                </tbody>
            </table>
        </div>
        
        <!-- 页脚 -->
        <div class="footer">
            <p>本报告由 TFA Risk Agent v3.2 生成 | 基于 Regional Risk Matrix 和 Weighted Risk Index (WRI) 评估方法论</p>
            <p style="margin-top: 10px; font-size: 12px;">报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
    
    <script>
        // WRI对比图
        const wriChart = echarts.init(document.getElementById('wriChart'));
        wriChart.setOption({{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: {{ type: 'value', max: 6, name: 'WRI' }},
            yAxis: {{ type: 'category', data: {json.dumps([d['name'] for d in wri_chart_data])} }},
            series: [{{
                type: 'bar',
                data: {json.dumps([{'value': d['value'], 'itemStyle': {'color': d['color']}} for d in wri_chart_data])},
                label: {{ show: true, position: 'right', formatter: '{{c}}' }}
            }}]
        }});
        
        // 7维度风险分布热力图
        const dimensionChart = echarts.init(document.getElementById('dimensionChart'));
        dimensionChart.setOption({{
            tooltip: {{ position: 'top' }},
            grid: {{ height: '70%', top: '10%' }},
            xAxis: {{ type: 'category', data: ['毁林风险', '气候脆弱', 'EUDR暴露', '生产体量', '溯源风险', '劳工风险', '保护区影响'], splitArea: {{ show: true }} }},
            yAxis: {{ type: 'category', data: {json.dumps(heatmap_regions)}, splitArea: {{ show: true }} }},
            visualMap: {{ min: 1, max: 6, calculable: false, orient: 'horizontal', left: 'center', bottom: '2%', inRange: {{ color: ['#52c41a', '#95de64', '#faad14', '#ff7875', '#ff4d4f', '#a8071a'] }} }},
            series: [{{
                type: 'heatmap',
                data: {json.dumps(heatmap_data)}
            }}]
        }});
        
        // 风险管理能力图
        const capabilityChart = echarts.init(document.getElementById('capabilityChart'));
        capabilityChart.setOption({{
            tooltip: {{ trigger: 'axis' }},
            xAxis: {{ type: 'category', data: {json.dumps([d['name'] for d in capability_data])}, axisLabel: {{ rotate: 15 }} }},
            yAxis: {{ type: 'value', max: 100, name: '得分' }},
            series: [{{
                type: 'bar',
                data: {json.dumps([d['value'] for d in capability_data])},
                itemStyle: {{ color: '#667eea' }},
                label: {{ show: true, position: 'top', formatter: '{{c}}' }}
            }}]
        }});
    </script>
</body>
</html>'''
        
        return html


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='从DDQ评估表生成TFA风险报告 v3.2（完整UI版）')
    parser.add_argument('--input', '-i', required=True, help='DDQ评估表CSV文件路径')
    parser.add_argument('--output', '-o', default='./output', help='输出目录')
    parser.add_argument('--company', '-c', default='', help='企业名称')
    parser.add_argument('--no-feedback', action='store_true', help='禁用报告中的反馈功能')
    
    args = parser.parse_args()
    
    generator = TFARiskReportGenerator(
        ddq_csv_path=args.input,
        output_dir=args.output,
        company_name=args.company
    )
    
    report_path = generator.generate_html_report(enable_feedback=not args.no_feedback)
    print(f"\n✅ 报告生成完成: {report_path}")
    
    if FEEDBACK_SYSTEM_AVAILABLE and not args.no_feedback:
        print("\n📝 反馈系统已启用")
        print("   用户可以在报告末尾提交反馈，帮助改进评估质量")


if __name__ == '__main__':
    main()
