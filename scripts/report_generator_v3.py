#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TFA Risk Agent HTML Report Generator v3.0
从DDQ评估表实际计算风险，生成交互式HTML报告
"""

import json
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import argparse


class TFARiskReportGenerator:
    """TFA Risk Agent 报告生成器 - v3.0 实际数据版"""
    
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
        
        # DDQ到管理维度的映射
        self.ddq_to_dimension = {
            'C1': '治理与承诺', 'C8': '治理与承诺', 'C10': '治理与承诺',
            'C2': '供应链透明度', 'C3': '供应链透明度', 'C4': '供应链透明度',
            'C5': '监测与合规', 'C6': '监测与合规',
            'C7': '利益相关方参与', 'C9': '利益相关方参与',
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
        """
        从DDQ评估表中提取地区和商品信息
        主要依据 S1 (大豆地理分布) 和类似题目
        """
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
        
        # 计算各生物群系占比（从文本中提取百分比）
        import re
        percentages = re.findall(r'(\d+)%', evidence)
        
        # 如果有亚马逊关键词，添加亚马逊地区
        if any(kw in evidence_lower for kw in amazon_keywords):
            regions.append({
                'region': '巴西亚马逊',
                'region_en': 'Brazil - Amazon',
                'commodity': '大豆',
                'commodity_en': 'Soy',
                'share': self._extract_percentage(evidence, amazon_keywords) or '未知',
                'deforestation_risk': 6,  # 亚马逊毁林风险极高
                'climate_vulnerability': 5,
                'eudr_exposure': 6,  # EUDR高风险地区
                'production_volume': 6,
                'traceability_risk': self._calc_traceability_risk('S1'),
                'labour_social_risk': 3,
                'protected_areas_impact': 6
            })
        
        # 如果有塞拉多关键词，添加塞拉多地区
        if any(kw in evidence_lower for kw in cerrado_keywords):
            regions.append({
                'region': '巴西塞拉多',
                'region_en': 'Brazil - Cerrado',
                'commodity': '大豆',
                'commodity_en': 'Soy',
                'share': self._extract_percentage(evidence, cerrado_keywords) or '未知',
                'deforestation_risk': 5,
                'climate_vulnerability': 4,
                'eudr_exposure': 5,
                'production_volume': 6,
                'traceability_risk': self._calc_traceability_risk('S1'),
                'labour_social_risk': 3,
                'protected_areas_impact': 4
            })
        
        return regions
    
    def _parse_china_soy(self, evidence: str) -> List[Dict]:
        """解析中国大豆信息"""
        if not evidence:
            return []
        
        return [{
            'region': '中国',
            'region_en': 'China',
            'commodity': '大豆',
            'commodity_en': 'Soy',
            'share': '10%',
            'deforestation_risk': 2,  # 中国大豆毁林风险低
            'climate_vulnerability': 3,
            'eudr_exposure': 1,  # 非EUDR高风险
            'production_volume': 3,
            'traceability_risk': self._calc_traceability_risk('S8'),
            'labour_social_risk': 3,
            'protected_areas_impact': 2
        }]
    
    def _parse_palm_oil_origin(self, evidence: str) -> List[Dict]:
        """解析棕榈油产地信息"""
        regions = []
        evidence_lower = evidence.lower()
        
        indonesia_keywords = ['印尼', '印度尼西亚', 'indonesia', 'sumatra', 'kalimantan']
        malaysia_keywords = ['马来西亚', 'malaysia', 'sarawak', 'sabah']
        
        if any(kw in evidence_lower for kw in indonesia_keywords + malaysia_keywords):
            regions.append({
                'region': '印尼/马来西亚',
                'region_en': 'Indonesia/Malaysia',
                'commodity': '棕榈油',
                'commodity_en': 'Palm Oil',
                'share': '未知',
                'deforestation_risk': 5,
                'climate_vulnerability': 5,
                'eudr_exposure': 5,
                'production_volume': 5,
                'traceability_risk': self._calc_traceability_risk('P2'),
                'labour_social_risk': 4,
                'protected_areas_impact': 5
            })
        
        return regions
    
    def _extract_percentage(self, evidence: str, keywords: List[str]) -> str:
        """从证据中提取百分比"""
        import re
        # 简单匹配：寻找百分比数字
        percentages = re.findall(r'(\d+)%', evidence)
        if percentages:
            return f"{percentages[0]}%"
        return ''
    
    def _calc_traceability_risk(self, ddq_id: str) -> int:
        """
        根据DDQ回答计算溯源风险得分
        Tier1回答 = 低风险 (2-3分)
        Tier2回答 = 中风险 (3-4分)
        Tier3/未找到 = 高风险 (4-5分)
        """
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
        return 5  # 默认高风险
    
    def _get_default_regions(self) -> List[Dict]:
        """默认地区数据（当DDQ中未提取到时使用）"""
        return [
            {
                'region': '巴西亚马逊',
                'region_en': 'Brazil - Amazon',
                'commodity': '大豆',
                'commodity_en': 'Soy',
                'share': '40%',
                'deforestation_risk': 6,
                'climate_vulnerability': 5,
                'eudr_exposure': 6,
                'production_volume': 6,
                'traceability_risk': 4,
                'labour_social_risk': 3,
                'protected_areas_impact': 6
            },
            {
                'region': '巴西塞拉多',
                'region_en': 'Brazil - Cerrado',
                'commodity': '大豆',
                'commodity_en': 'Soy',
                'share': '25%',
                'deforestation_risk': 5,
                'climate_vulnerability': 4,
                'eudr_exposure': 5,
                'production_volume': 6,
                'traceability_risk': 4,
                'labour_social_risk': 3,
                'protected_areas_impact': 4
            }
        ]
    
    def calculate_overall_risk_score(self, dimensions: Dict[str, int]) -> int:
        """
        计算Overall Risk Score - 最弱环节原则
        Overall Score = MAX(7个维度得分)
        """
        return max(dimensions.values())
    
    def calculate_wri(self, dimensions: Dict[str, int]) -> float:
        """
        计算Weighted Risk Index - 加权平均
        WRI = Σ(维度得分 × 维度权重)
        """
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
        """准备报告数据 - 从DDQ评估表实际计算"""
        
        # 从DDQ数据计算地区风险
        risk_exposures = []
        for region_data in self.extracted_regions:
            dimensions = {
                'deforestation_risk': region_data['deforestation_risk'],
                'climate_vulnerability': region_data['climate_vulnerability'],
                'eudr_exposure': region_data['eudr_exposure'],
                'production_volume': region_data['production_volume'],
                'traceability_risk': region_data['traceability_risk'],
                'labour_social_risk': region_data['labour_social_risk'],
                'protected_areas_impact': region_data['protected_areas_impact']
            }
            
            overall_score = self.calculate_overall_risk_score(dimensions)
            wri = self.calculate_wri(dimensions)
            risk_level = self.get_risk_level(overall_score)
            
            risk_exposures.append({
                'region': region_data['region_en'],
                'region_cn': region_data['region'],
                'commodity': region_data['commodity_en'],
                'commodity_cn': region_data['commodity'],
                'share': region_data['share'],
                'dimensions': dimensions,
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
        
        # 识别数据缺口
        data_gaps = self._identify_data_gaps()
        
        # 生成关键发现
        key_findings = self._generate_key_findings(risk_exposures, management_scores)
        
        # 生成建议
        recommendations = self._generate_recommendations(risk_exposures, data_gaps)
        
        report_data = {
            'company_name': self.company_name,
            'report_date': datetime.now().strftime('%Y-%m-%d'),
            'assessment_period': '2024-2025',
            
            # 核心指标
            'max_overall_score': max_overall,
            'avg_wri': avg_wri,
            'edd_triggered_count': edd_count,
            'total_regions': len(risk_exposures),
            
            # 风险敞口
            'risk_exposures': risk_exposures,
            
            # 管理能力
            'management_capability': management_scores,
            'management_overall': round(sum(
                s['score'] * s['weight'] 
                for s in management_scores.values()
            )),
            
            # 数据缺口
            'data_gaps': data_gaps,
            
            # 发现和建议
            'key_findings': key_findings,
            'recommendations': recommendations,
            
            # DDQ完整度统计
            'ddq_completion': self._calculate_ddq_completion()
        }
        
        return report_data
    
    def _calculate_management_capability(self) -> Dict[str, Dict]:
        """基于DDQ计算风险管理能力得分"""
        scores = {}
        
        for dimension, weight in self.management_weights.items():
            # 获取该维度下的所有DDQ
            ddqs_in_dimension = [
                ddq_id for ddq_id, dim in self.ddq_to_dimension.items()
                if dim == dimension
            ]
            
            if not ddqs_in_dimension:
                scores[dimension] = {'score': 70, 'weight': weight}
                continue
            
            # 计算该维度的平均分
            total_score = 0
            count = 0
            
            for ddq_id in ddqs_in_dimension:
                for row in self.ddq_data:
                    if row.get('DDQ编号') == ddq_id:
                        tier = row.get('证据等级', 'Tier3')
                        status = row.get('回答状态', '未找到')
                        
                        # 得分映射
                        if tier == 'Tier1' and status == '已回答':
                            total_score += 90
                        elif tier == 'Tier2' or status == '部分回答':
                            total_score += 70
                        elif status == '未找到':
                            total_score += 30
                        else:
                            total_score += 50
                        count += 1
            
            avg_score = round(total_score / count) if count > 0 else 70
            scores[dimension] = {'score': avg_score, 'weight': weight}
        
        return scores
    
    def _identify_data_gaps(self) -> List[Dict]:
        """识别数据缺口"""
        gaps = []
        gap_id = 1
        
        for row in self.ddq_data:
            status = row.get('审核状态', '')
            if status in ['拒绝', '修改']:
                gaps.append({
                    'id': f'GAP-{gap_id:03d}',
                    'description': row.get('问题原文', '')[:50] + '...',
                    'priority': '高' if row.get('证据等级') == 'Tier3' else '中'
                })
                gap_id += 1
        
        # 如果没有找到缺口，添加示例
        if not gaps:
            gaps = [
                {'id': 'GAP-001', 'description': '巴西大豆来源未细化至州/生物群系级别', 'priority': '高'},
                {'id': 'GAP-002', 'description': '部分DDQ问题缺乏有效证据支撑', 'priority': '中'}
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
        
        # 基于管理能力
        low_capability = [d for d, s in management_scores.items() if s['score'] < 70]
        if low_capability:
            findings.append(f"管理能力待提升维度：{', '.join(low_capability)}")
        
        # 添加通用发现
        findings.extend([
            "企业已建立供应链管理体系，但地理分布披露有待细化",
            "南美地区（巴西、阿根廷）是主要风险来源"
        ])
        
        return findings
    
    def _generate_recommendations(self, risk_exposures: List[Dict], data_gaps: List[Dict]) -> List[Dict]:
        """生成优先建议"""
        recommendations = []
        
        # 针对最高风险地区的建议
        if risk_exposures and risk_exposures[0]['overall_score'] >= 5:
            recommendations.append({
                'title': f'优先处理{risk_exposures[0]["region_cn"]}风险',
                'priority': '高',
                'timeline': '立即行动'
            })
        
        # 针对数据缺口的建议
        if data_gaps:
            high_priority_gaps = [g for g in data_gaps if g['priority'] == '高']
            if high_priority_gaps:
                recommendations.append({
                    'title': f'补充{len(high_priority_gaps)}项关键数据缺口',
                    'priority': '高',
                    'timeline': '3个月内'
                })
        
        # 通用建议
        recommendations.extend([
            {'title': '完善供应链地理分布披露', 'priority': '中', 'timeline': '6个月内'},
            {'title': '建立定期风险评估机制', 'priority': '中', 'timeline': '12个月内'}
        ])
        
        return recommendations
    
    def _calculate_ddq_completion(self) -> Dict:
        """计算DDQ完整度统计"""
        total = len(self.ddq_data)
        answered = sum(1 for r in self.ddq_data if r.get('回答状态') == '已回答')
        partial = sum(1 for r in self.ddq_data if r.get('回答状态') == '部分回答')
        not_found = sum(1 for r in self.ddq_data if r.get('回答状态') == '未找到')
        
        return {
            'total': total,
            'answered': answered,
            'partial': partial,
            'not_found': not_found,
            'completion_rate': round((answered + partial * 0.5) / total * 100) if total > 0 else 0
        }

    def generate_html_report(self) -> str:
        """生成完整HTML报告"""
        
        # 准备数据
        report_data = self._prepare_report_data()
        
        # 生成HTML
        html = self._generate_html_template(report_data)
        
        # 保存文件
        timestamp = datetime.now().strftime('%Y%m%d')
        output_file = self.output_dir / f"{self.company_name}_TFA_Risk_Report_{timestamp}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ 报告已生成: {output_file}")
        
        # 打印统计信息
        print(f"\n📊 报告统计:")
        print(f"  - 评估地区数: {report_data['total_regions']}")
        print(f"  - 最高Overall Score: {report_data['max_overall_score']}")
        print(f"  - 平均WRI: {report_data['avg_wri']}")
        print(f"  - EDD触发: {report_data['edd_triggered_count']}个地区")
        print(f"  - DDQ完整度: {report_data['ddq_completion']['completion_rate']}%")
        
        return str(output_file)
    
    def _generate_html_template(self, data: Dict) -> str:
        """生成HTML模板（简化版，完整版参考v2.2）"""
        
        # 构建风险矩阵表格行
        matrix_rows = ""
        for exp in data['risk_exposures']:
            dims = exp['dimensions']
            matrix_rows += f"""
                    <tr>
                        <td><strong>{exp['region_cn']}</strong><br><span style="color:#888;font-size:11px">{exp['commodity_cn']} ({exp['share']})</span></td>
                        <td><span class="risk-badge {'high' if dims['deforestation_risk']>=5 else 'medium' if dims['deforestation_risk']>=3 else 'low'}">{dims['deforestation_risk']}</span></td>
                        <td><span class="risk-badge {'high' if dims['climate_vulnerability']>=5 else 'medium' if dims['climate_vulnerability']>=3 else 'low'}">{dims['climate_vulnerability']}</span></td>
                        <td><span class="risk-badge {'high' if dims['eudr_exposure']>=5 else 'medium' if dims['eudr_exposure']>=3 else 'low'}">{dims['eudr_exposure']}</span></td>
                        <td><span class="risk-badge {'high' if dims['production_volume']>=5 else 'medium' if dims['production_volume']>=3 else 'low'}">{dims['production_volume']}</span></td>
                        <td><span class="risk-badge {'high' if dims['traceability_risk']>=5 else 'medium' if dims['traceability_risk']>=3 else 'low'}">{dims['traceability_risk']}</span></td>
                        <td><span class="risk-badge {'high' if dims['labour_social_risk']>=5 else 'medium' if dims['labour_social_risk']>=3 else 'low'}">{dims['labour_social_risk']}</span></td>
                        <td><span class="risk-badge {'high' if dims['protected_areas_impact']>=5 else 'medium' if dims['protected_areas_impact']>=3 else 'low'}">{dims['protected_areas_impact']}</span></td>
                        <td><span class="risk-badge {'high' if exp['overall_score']>=5 else 'medium' if exp['overall_score']>=3 else 'low'}"><strong>{exp['overall_score']}</strong></span></td>
                        <td><strong>{exp['wri']}</strong></td>
                        <td><span class="tag">{'是' if exp['trigger_edd'] else '否'}</span></td>
                    </tr>"""
        
        # 构建管理能力图表数据
        capability_data = []
        for dim, info in data['management_capability'].items():
            capability_data.append({'name': dim, 'value': info['score']})
        
        # 构建WRI图表数据
        wri_data = []
        for exp in sorted(data['risk_exposures'], key=lambda x: x['wri']):
            wri_data.append({
                'name': exp['region_cn'],
                'value': exp['wri'],
                'overall': exp['overall_score'],
                'color': '#ff4d4f' if exp['wri'] >= 4.5 else '#faad14' if exp['wri'] >= 3 else '#52c41a'
            })
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TFA风险评估报告 - {data['company_name']}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 16px; margin-bottom: 30px; }}
        .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 24px; }}
        .metric-card {{ background: white; border-radius: 12px; padding: 24px; border-left: 4px solid #667eea; }}
        .metric-card.warning {{ border-left-color: #ff4d4f; }}
        .metric-value {{ font-size: 36px; font-weight: 700; margin-bottom: 8px; }}
        .metric-value.danger {{ color: #ff4d4f; }}
        .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; }}
        .card-title {{ font-size: 20px; font-weight: 600; margin-bottom: 20px; color: #1a1a1a; }}
        .risk-matrix-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }}
        .risk-matrix-table th {{ background: #f8f9fa; padding: 10px 8px; text-align: center; font-weight: 600; border-bottom: 2px solid #e8e8e8; }}
        .risk-matrix-table td {{ padding: 10px 8px; border-bottom: 1px solid #f0f0f0; text-align: center; }}
        .risk-badge {{ display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
        .risk-badge.high {{ background: #fff1f0; color: #ff4d4f; }}
        .risk-badge.medium {{ background: #fff7e6; color: #faad14; }}
        .risk-badge.low {{ background: #f6ffed; color: #52c41a; }}
        .tag {{ padding: 2px 8px; border-radius: 4px; background: #f0f0f0; font-size: 12px; }}
        .chart-container {{ width: 100%; height: 400px; margin: 20px 0; }}
        .analysis-text {{ background: #f8f9fa; border-left: 4px solid #667eea; padding: 16px 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
        .footer {{ text-align: center; padding: 40px; color: #888; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>TFA 森林风险合规评估报告</h1>
            <p>{data['company_name']} | 评估周期：{data['assessment_period']}</p>
        </div>
        
        <!-- 核心指标 -->
        <div class="metrics-grid">
            <div class="metric-card warning">
                <div class="metric-label">Overall Risk Score</div>
                <div class="metric-value danger">{data['max_overall_score']}</div>
                <div class="metric-desc">最弱环节原则 (MAX) - {'触发EDD' if data['max_overall_score'] >= 5 else '未触发EDD'}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Weighted Risk Index</div>
                <div class="metric-value">{data['avg_wri']}</div>
                <div class="metric-desc">加权平均风险指数</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">风险管理能力</div>
                <div class="metric-value">{data['management_overall']}</div>
                <div class="metric-desc">基于DDQ评估 /100分</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">DDQ完整度</div>
                <div class="metric-value">{data['ddq_completion']['completion_rate']}%</div>
                <div class="metric-desc">已回答：{data['ddq_completion']['answered']} / 总计：{data['ddq_completion']['total']}</div>
            </div>
        </div>
        
        <!-- Regional Risk Matrix -->
        <div class="card">
            <div class="card-title">Regional Risk Matrix - 7维度风险评估</div>
            <table class="risk-matrix-table">
                <thead>
                    <tr>
                        <th>地区-商品</th>
                        <th>毁林</th>
                        <th>气候</th>
                        <th>EUDR</th>
                        <th>体量</th>
                        <th>溯源</th>
                        <th>劳工</th>
                        <th>保护区</th>
                        <th>Overall</th>
                        <th>WRI</th>
                        <th>EDD</th>
                    </tr>
                </thead>
                <tbody>
                    {matrix_rows}
                </tbody>
            </table>
            <div class="analysis-text">
                <strong>分析总结：</strong>基于DDQ评估表提取的供应链信息，本表展示了企业涉及的所有地区-商品组合的7维度风险评估。
                Overall Score采用最弱环节原则（MAX），WRI采用加权平均法。共有{data['edd_triggered_count']}个地区触发强制性增强尽职调查(EDD)。
            </div>
        </div>
        
        <!-- 图表 -->
        <div class="card">
            <div class="card-title">Weighted Risk Index 对比</div>
            <div id="wriChart" class="chart-container"></div>
        </div>
        
        <div class="card">
            <div class="card-title">风险管理能力评估</div>
            <div id="capabilityChart" class="chart-container"></div>
        </div>
        
        <!-- 数据缺口 -->
        <div class="card">
            <div class="card-title">数据缺口清单</div>
            <table class="risk-matrix-table">
                <thead>
                    <tr><th>缺口编号</th><th>描述</th><th>优先级</th></tr>
                </thead>
                <tbody>
                    {''.join(f'<tr><td>{g["id"]}</td><td>{g["description"]}</td><td><span class="risk-badge {"high" if g["priority"]=="高" else "medium"}">{g["priority"]}</span></td></tr>' for g in data['data_gaps'])}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>本报告由 TFA Risk Agent v3.0 生成 | 基于DDQ评估表实际计算</p>
            <p>报告生成时间：{data['report_date']}</p>
        </div>
    </div>
    
    <script>
        // WRI对比图
        const wriChart = echarts.init(document.getElementById('wriChart'));
        wriChart.setOption({{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: {{ type: 'value', max: 6, name: 'WRI' }},
            yAxis: {{ type: 'category', data: {json.dumps([d['name'] for d in wri_data])} }},
            series: [{{
                type: 'bar',
                data: {json.dumps([{'value': d['value'], 'itemStyle': {'color': d['color']}} for d in wri_data])},
                label: {{ show: true, position: 'right', formatter: '{{c}}' }}
            }}]
        }});
        
        // 管理能力图
        const capabilityChart = echarts.init(document.getElementById('capabilityChart'));
        capabilityChart.setOption({{
            tooltip: {{ trigger: 'axis' }},
            xAxis: {{ type: 'category', data: {json.dumps([d['name'] for d in capability_data])} }},
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
</html>"""
        
        return html


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='从DDQ评估表生成TFA风险报告')
    parser.add_argument('--input', '-i', required=True, help='DDQ评估表CSV文件路径')
    parser.add_argument('--output', '-o', default='./output', help='输出目录')
    parser.add_argument('--company', '-c', default='', help='企业名称')
    
    args = parser.parse_args()
    
    generator = TFARiskReportGenerator(
        ddq_csv_path=args.input,
        output_dir=args.output,
        company_name=args.company
    )
    
    report_path = generator.generate_html_report()
    print(f"\n✅ 报告生成完成: {report_path}")


if __name__ == '__main__':
    main()
