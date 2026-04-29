#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from datetime import datetime

# 读取安踏数据
with open('/tmp/anta_report_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 辅助函数
def get_badge_class(score):
    if score >= 5:
        return 'high'
    elif score >= 3:
        return 'medium'
    return 'low'

# 构建完整HTML
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TFA Risk Assessment Report - {data['company_name']}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 16px; margin-bottom: 30px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }}
        .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        .header .subtitle {{ font-size: 16px; opacity: 0.9; }}
        .header .meta {{ margin-top: 20px; display: flex; gap: 30px; flex-wrap: wrap; }}
        .header .meta-item {{ display: flex; flex-direction: column; }}
        .header .meta-label {{ font-size: 12px; opacity: 0.7; text-transform: uppercase; }}
        .header .meta-value {{ font-size: 18px; font-weight: 600; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 24px; }}
        .metric-card {{ background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid #667eea; }}
        .metric-card.warning {{ border-left-color: #ff4d4f; }}
        .metric-card.success {{ border-left-color: #52c41a; }}
        .metric-label {{ font-size: 14px; color: #666; margin-bottom: 8px; }}
        .metric-value {{ font-size: 36px; font-weight: 700; margin-bottom: 8px; }}
        .metric-value.danger {{ color: #ff4d4f; }}
        .metric-value.success {{ color: #52c41a; }}
        .metric-value.warning {{ color: #faad14; }}
        .metric-desc {{ font-size: 13px; color: #888; }}
        .progress-bar {{ width: 100%; height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden; margin: 8px 0; }}
        .progress-fill {{ height: 100%; border-radius: 4px; transition: width 0.5s ease; }}
        .progress-fill.danger {{ background: linear-gradient(90deg, #ff4d4f, #ff7875); }}
        .progress-fill.warning {{ background: linear-gradient(90deg, #faad14, #ffc53d); }}
        .progress-fill.success {{ background: linear-gradient(90deg, #52c41a, #73d13d); }}
        .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .card-title {{ font-size: 20px; font-weight: 600; margin-bottom: 20px; color: #1a1a1a; display: flex; align-items: center; gap: 10px; }}
        .card-title::before {{ content: ''; width: 4px; height: 20px; background: #667eea; border-radius: 2px; }}
        .risk-matrix-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }}
        .risk-matrix-table th {{ background: #f8f9fa; padding: 10px 8px; text-align: center; font-weight: 600; color: #666; border-bottom: 2px solid #e8e8e8; font-size: 12px; }}
        .risk-matrix-table td {{ padding: 10px 8px; border-bottom: 1px solid #f0f0f0; text-align: center; }}
        .risk-matrix-table tr:hover {{ background: #fafafa; }}
        .risk-matrix-table td:first-child {{ text-align: left; font-weight: 500; }}
        .risk-badge {{ display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
        .risk-badge.high {{ background: #fff1f0; color: #ff4d4f; }}
        .risk-badge.medium {{ background: #fff7e6; color: #faad14; }}
        .risk-badge.low {{ background: #f6ffed; color: #52c41a; }}
        .tag {{ display: inline-block; padding: 4px 8px; background: #f0f0f0; border-radius: 4px; font-size: 12px; color: #666; }}
        .tag.edd {{ background: #ff4d4f; color: white; }}
        .chart-container {{ width: 100%; height: 400px; margin: 20px 0; }}
        .analysis-text {{ background: #f8f9fa; border-left: 4px solid #667eea; padding: 16px 20px; margin: 20px 0; border-radius: 0 8px 8px 0; font-size: 14px; line-height: 1.8; color: #555; }}
        .analysis-text strong {{ color: #333; }}
        .findings-list {{ list-style: none; }}
        .findings-list li {{ padding: 12px 0; border-bottom: 1px solid #f0f0f0; display: flex; align-items: flex-start; gap: 12px; }}
        .findings-list li:last-child {{ border-bottom: none; }}
        .findings-list .icon {{ width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; }}
        .findings-list .icon.warning {{ background: #fff7e6; color: #faad14; }}
        .findings-list .icon.success {{ background: #f6ffed; color: #52c41a; }}
        .recommendation-card {{ background: #fafafa; border-radius: 8px; padding: 16px; margin-bottom: 12px; border-left: 4px solid #667eea; }}
        .recommendation-card.high {{ border-left-color: #ff4d4f; background: #fff1f0; }}
        .recommendation-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
        .recommendation-title {{ font-weight: 600; }}
        .recommendation-meta {{ display: flex; gap: 12px; font-size: 13px; color: #666; }}
        .priority-badge {{ padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .priority-badge.high {{ background: #ff4d4f; color: white; }}
        .match-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
        .match-table th {{ background: #f8f9fa; padding: 12px; text-align: left; font-weight: 600; color: #666; border-bottom: 2px solid #e8e8e8; }}
        .match-table td {{ padding: 12px; border-bottom: 1px solid #f0f0f0; }}
        .match-table tr:hover {{ background: #fafafa; }}
        .two-columns {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        @media (max-width: 768px) {{ .two-columns {{ grid-template-columns: 1fr; }} .metrics-grid {{ grid-template-columns: 1fr; }} .header h1 {{ font-size: 24px; }} }}
        .footer {{ text-align: center; padding: 40px; color: #999; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
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
        
        <div class="metrics-grid">
            <div class="metric-card warning">
                <div class="metric-label">Overall Risk Score</div>
                <div class="metric-value danger">{data['edd_triggered_count']}个地区</div>
                <div class="metric-desc">触发强制性增强尽职调查 (EDD)</div>
                <div class="progress-bar">
                    <div class="progress-fill danger" style="width: 60%"></div>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Weighted Risk Index (WRI)</div>
                <div class="metric-value warning">{data['avg_wri']}/6.0</div>
                <div class="metric-desc">企业综合风险指数 ({int(data['avg_wri']/6*100)}%)</div>
                <div class="progress-bar">
                    <div class="progress-fill warning" style="width: 80%"></div>
                </div>
            </div>
            <div class="metric-card success">
                <div class="metric-label">风险管理能力</div>
                <div class="metric-value success">{data['management_overall']}/100</div>
                <div class="metric-desc">评级：中等</div>
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
'''

# 添加风险矩阵
html += '''
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
'''

for exp in data['risk_exposures']:
    dims = exp['dimensions']
    edd_badge = '<span class="tag edd">是</span>' if exp['trigger_edd'] else '<span class="tag">否</span>'
    
    html += f'''                    <tr>
                        <td><strong>{exp['region']}</strong><br><span style="color:#888;font-size:11px">{exp['commodity_cn']} ({exp['share']})</span></td>
                        <td><span class="risk-badge {get_badge_class(dims['deforestation_risk'])}">{dims['deforestation_risk']}</span></td>
                        <td><span class="risk-badge {get_badge_class(dims['climate_vulnerability'])}">{dims['climate_vulnerability']}</span></td>
                        <td><span class="risk-badge {get_badge_class(dims['eudr_exposure'])}">{dims['eudr_exposure']}</span></td>
                        <td><span class="risk-badge {get_badge_class(dims['production_volume'])}">{dims['production_volume']}</span></td>
                        <td><span class="risk-badge {get_badge_class(dims['traceability_risk'])}">{dims['traceability_risk']}</span></td>
                        <td><span class="risk-badge {get_badge_class(dims['labour_social_risk'])}">{dims['labour_social_risk']}</span></td>
                        <td><span class="risk-badge {get_badge_class(dims['protected_areas_impact'])}">{dims['protected_areas_impact']}</span></td>
                        <td><span class="risk-badge {get_badge_class(exp['overall_score'])}"><strong>{exp['overall_score']}</strong></span></td>
                        <td><strong>{exp['wri']}</strong></td>
                        <td>{edd_badge}</td>
                    </tr>
'''

html += '''                </tbody>
            </table>
            <div class="analysis-text">
                <strong>分析总结：</strong>本表基于Weighted Risk Index评估方法，对安踏体育供应链涉及的6个地区-商品组合进行7维度风险评估。
                <strong>关键发现：</strong>巴西亚马逊（皮革）在毁林风险(6)、EUDR暴露(6)、保护区影响(6)三个维度均达到极高风险，Overall Score为6（最弱环节原则），WRI为5.2（加权平均）。印度尼西亚（橡胶）EUDR暴露和气候脆弱性均为高风险。企业共有3个地区触发强制性增强尽职调查(EDD)。
            </div>
        </div>
'''

print("第一部分已生成")

# 保存
with open('output/安踏体育_最终版_TFA_Risk_Report.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ 报告第一部分已保存")

EOF
