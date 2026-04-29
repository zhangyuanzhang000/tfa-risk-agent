"""
TFA Risk Agent 反馈收集集成模块

此模块提供在DDQ评估表和HTML报告中嵌入反馈收集功能的方法。

使用方式:
1. 在DDQ评估表CSV中添加反馈列
2. 在HTML报告中添加反馈按钮和表单
3. 收集到的反馈自动保存到feedback/目录
"""

import json
from datetime import datetime
from pathlib import Path

FEEDBACK_DIR = Path(__file__).parent.parent / "feedback"


def generate_ddq_feedback_template(ddq_id: str, current_data: dict) -> dict:
    """
    生成DDQ反馈模板
    
    Args:
        ddq_id: DDQ问题编号（如 C1, S1）
        current_data: 当前的评估数据
        
    Returns:
        反馈表单模板
    """
    return {
        "feedback_prompt": f"""
┌─────────────────────────────────────────────────────────────┐
📋 DDQ {ddq_id} 反馈

当前评估结果：
- 证据来源: {current_data.get('evidence_source', 'N/A')}
- 页码/段落: {current_data.get('page_number', 'N/A')}
- 证据等级: {current_data.get('evidence_tier', 'N/A')}
- 回答状态: {current_data.get('answer_status', 'N/A')}

如果发现以上信息有误，请提供反馈：

[✓] 完全正确
[ ] 证据位置有误（请说明正确位置）
[ ] 证据等级有误（应为 Tier1/Tier2/Tier3）
[ ] 回答状态有误（应为 已回答/部分/未找到）
[ ] 其他问题

修正说明：_________________________

请将此反馈发送给Agent以帮助我们改进。
└─────────────────────────────────────────────────────────────┘
""",
        "feedback_data": {
            "ddq_id": ddq_id,
            "assessment_id": current_data.get("assessment_id"),
            "original": {
                "evidence_source": current_data.get("evidence_source"),
                "page_number": current_data.get("page_number"),
                "evidence_tier": current_data.get("evidence_tier"),
                "answer_status": current_data.get("answer_status")
            }
        }
    }


def generate_html_feedback_component() -> str:
    """
    生成HTML报告中的反馈组件（JavaScript + HTML）
    
    Returns:
        HTML和JavaScript代码字符串
    """
    return """
<!-- TFA Risk Agent 反馈收集组件 -->
<div id="feedback-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; 
     background:rgba(0,0,0,0.5); z-index:1000; justify-content:center; align-items:center;">
    <div style="background:white; padding:30px; border-radius:10px; max-width:500px; width:90%;">
        <h3>📝 帮助我们改进</h3>
        <p id="feedback-context" style="color:#666; font-size:14px;"></p>
        
        <div style="margin:20px 0;">
            <label style="display:block; margin-bottom:10px;">请选择反馈类型：</label>
            <select id="feedback-type" style="width:100%; padding:8px; border:1px solid #ddd; border-radius:4px;">
                <option value="">-- 选择类型 --</option>
                <option value="evidence_location">证据位置不准确</option>
                <option value="answer_status">回答状态判定错误</option>
                <option value="tier_level">证据等级划分不当</option>
                <option value="calculation_error">风险计算有误</option>
                <option value="visualization_error">图表显示错误</option>
                <option value="other">其他问题</option>
            </select>
        </div>
        
        <div style="margin:20px 0;">
            <label style="display:block; margin-bottom:10px;">详细说明：</label>
            <textarea id="feedback-detail" rows="4" style="width:100%; padding:8px; border:1px solid #ddd; 
                      border-radius:4px; resize:vertical;" placeholder="请描述问题..."></textarea>
        </div>
        
        <div style="margin:20px 0;">
            <label style="display:block; margin-bottom:10px;">正确值（如果有）：</label>
            <input type="text" id="feedback-correction" style="width:100%; padding:8px; border:1px solid #ddd; 
                   border-radius:4px;" placeholder="请提供正确的信息...">
        </div>
        
        <div style="display:flex; gap:10px; justify-content:flex-end;">
            <button onclick="closeFeedbackModal()" style="padding:10px 20px; border:1px solid #ddd; 
                    background:#f5f5f5; border-radius:4px; cursor:pointer;">取消</button>
            <button onclick="submitFeedback()" style="padding:10px 20px; border:none; background:#1890ff; 
                    color:white; border-radius:4px; cursor:pointer;">提交反馈</button>
        </div>
    </div>
</div>

<script>
// 反馈数据存储
let currentFeedbackContext = {};

// 显示反馈弹窗
function showFeedbackModal(context) {
    currentFeedbackContext = context;
    document.getElementById('feedback-context').textContent = 
        `正在反馈: ${context.section || '当前页面'}`;
    document.getElementById('feedback-modal').style.display = 'flex';
}

// 关闭反馈弹窗
function closeFeedbackModal() {
    document.getElementById('feedback-modal').style.display = 'none';
    document.getElementById('feedback-type').value = '';
    document.getElementById('feedback-detail').value = '';
    document.getElementById('feedback-correction').value = '';
}

// 提交反馈
function submitFeedback() {
    const type = document.getElementById('feedback-type').value;
    const detail = document.getElementById('feedback-detail').value;
    const correction = document.getElementById('feedback-correction').value;
    
    if (!type) {
        alert('请选择反馈类型');
        return;
    }
    
    const feedback = {
        timestamp: new Date().toISOString(),
        assessment_id: currentFeedbackContext.assessment_id,
        section: currentFeedbackContext.section,
        feedback_type: type,
        detail: detail,
        correction: correction,
        page_url: window.location.href
    };
    
    // 发送到后端（需要后端API支持）
    // 临时存储到localStorage
    let feedbacks = JSON.parse(localStorage.getItem('tfa_feedbacks') || '[]');
    feedbacks.push(feedback);
    localStorage.setItem('tfa_feedbacks', JSON.stringify(feedbacks));
    
    alert('感谢您的反馈！我们会尽快处理。');
    closeFeedbackModal();
}

// 在页面关闭时批量发送反馈
window.addEventListener('beforeunload', function() {
    const feedbacks = JSON.parse(localStorage.getItem('tfa_feedbacks') || '[]');
    if (feedbacks.length > 0) {
        // 这里可以调用后端API发送反馈
        // navigator.sendBeacon('/api/feedback/batch', JSON.stringify(feedbacks));
        console.log('待发送反馈:', feedbacks);
    }
});
</script>

<!-- 浮动反馈按钮 -->
<button onclick="showFeedbackModal({section: '整体报告', assessment_id: '当前评估'})" 
        style="position:fixed; bottom:30px; right:30px; width:60px; height:60px; 
               border-radius:50%; background:#1890ff; color:white; border:none; 
               font-size:24px; cursor:pointer; box-shadow:0 4px 12px rgba(0,0,0,0.15);
               z-index:999;">
    💬
</button>
"""


def generate_assessment_feedback_form(assessment_id: str) -> str:
    """
    生成评估完成后的整体满意度反馈表单
    
    Args:
        assessment_id: 评估ID
        
    Returns:
        Markdown格式的反馈表单
    """
    return f"""
---

## 📊 评估反馈

您的反馈将帮助我们持续改进TFA风险评估Agent。

### 整体满意度

请为本次评估体验打分（1-5分）：

- [ ] ⭐ 非常不满意
- [ ] ⭐⭐ 不满意  
- [ ] ⭐⭐⭐ 一般
- [ ] ⭐⭐⭐⭐ 满意
- [ ] ⭐⭐⭐⭐⭐ 非常满意

### 各环节评分

| 环节 | 非常不满意 | 不满意 | 一般 | 满意 | 非常满意 |
|------|-----------|--------|------|------|----------|
| 上传体验 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 解析准确性 | [ ] | [ ] | [ ] | [ ] | [ ] |
| DDQ覆盖度 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 报告质量 | [ ] | [ ] | [ ] | [ ] | [ ] |
| HTML可视化 | [ ] | [ ] | [ ] | [ ] | [ ] |

### 开放式反馈

**做得好的地方：**
```
[请在此填写]
```

**需要改进的地方：**
```
[请在此填写]
```

**希望有的功能：**
```
[请在此填写]
```

### 提交方式

请将此反馈表单发送给Agent，或发送至反馈收集邮箱。

**评估ID**: `{assessment_id}`

---
"""


def create_feedback_summary() -> dict:
    """
    创建反馈数据汇总
    
    Returns:
        反馈统计摘要
    """
    from feedback_collector import get_feedback_stats
    
    stats = get_feedback_stats(days=30)
    
    return {
        "summary_generated": datetime.now().isoformat(),
        "period_days": 30,
        "statistics": stats,
        "status": "success"
    }


if __name__ == "__main__":
    # 测试生成反馈组件
    print("=" * 60)
    print("HTML反馈组件代码：")
    print("=" * 60)
    print(generate_html_feedback_component())
    
    print("\n" + "=" * 60)
    print("评估反馈表单模板：")
    print("=" * 60)
    print(generate_assessment_feedback_form("asm_test_001"))
