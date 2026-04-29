"""
HTML报告反馈组件生成器
在TFA风险评估报告中嵌入反馈收集功能

用法:
    from feedback_embedder import FeedbackEmbedder
    
    embedder = FeedbackEmbedder(assessment_id="asm_xxx")
    feedback_html = embedder.generate_ddq_feedback_component(ddq_id="S1")
    report_html = embedder.inject_into_report(report_html)
"""

import json
import base64
from datetime import datetime


class FeedbackEmbedder:
    """在HTML报告中嵌入反馈组件"""
    
    def __init__(self, assessment_id: str, user_id: str = None):
        self.assessment_id = assessment_id
        self.user_id = user_id or "anonymous"
        
    def generate_ddq_feedback_component(self, ddq_id: str, context: dict = None) -> str:
        """
        为单个DDQ问题生成反馈组件
        
        Args:
            ddq_id: DDQ问题编号（如 S1, C1）
            context: 上下文信息，如当前证据、回答状态等
        """
        context_json = json.dumps(context or {}, ensure_ascii=False)
        context_b64 = base64.b64encode(context_json.encode()).decode()
        
        html = f'''
<!-- DDQ Feedback Component for {ddq_id} -->
<div class="ddq-feedback" id="feedback-{ddq_id}" data-ddq-id="{ddq_id}" data-context="{context_b64}">
    <div class="feedback-trigger">
        <button class="feedback-btn" onclick="toggleFeedbackForm('{ddq_id}')">
            <span>📝</span> 反馈
        </button>
    </div>
    <div class="feedback-form" id="form-{ddq_id}" style="display:none;">
        <p class="feedback-title">这个回答是否正确？</p>
        <div class="feedback-options">
            <button class="option-btn correct" onclick="submitFeedback('{ddq_id}', 'correct')">
                ✅ 正确
            </button>
            <button class="option-btn wrong" onclick="showCorrectionForm('{ddq_id}')">
                ❌ 有误
            </button>
        </div>
        <div class="correction-form" id="correction-{ddq_id}" style="display:none;">
            <p>请选择问题类型：</p>
            <select id="type-{ddq_id}" onchange="onCorrectionTypeChange('{ddq_id}')">
                <option value="">请选择...</option>
                <option value="evidence_location">证据定位错误（文件/页码）</option>
                <option value="answer_status">回答状态判定错误</option>
                <option value="tier_level">证据等级划分不当</option>
                <option value="other">其他问题</option>
            </select>
            <div id="correction-fields-{ddq_id}" style="display:none;margin-top:10px;">
                <textarea id="reason-{ddq_id}" placeholder="请描述正确的信息..." rows="3"></textarea>
            </div>
            <button class="submit-btn" onclick="submitCorrection('{ddq_id}')">提交修正</button>
        </div>
        <div class="feedback-thanks" id="thanks-{ddq_id}" style="display:none;">
            <p>✅ 感谢反馈！已记录。</p>
        </div>
    </div>
</div>
'''
        return html
    
    def generate_report_end_feedback(self) -> str:
        """生成报告末尾的整体反馈组件"""
        html = f'''
<!-- Report End Feedback Component -->
<div class="report-feedback-section" id="report-feedback">
    <h3>📝 评估反馈</h3>
    <p>您的反馈将帮助我们改进评估质量。</p>
    
    <div class="rating-section">
        <p><strong>整体满意度</strong></p>
        <div class="star-rating" id="overall-rating">
            <span class="star" onclick="rate('overall', 1)">★</span>
            <span class="star" onclick="rate('overall', 2)">★</span>
            <span class="star" onclick="rate('overall', 3)">★</span>
            <span class="star" onclick="rate('overall', 4)">★</span>
            <span class="star" onclick="rate('overall', 5)">★</span>
        </div>
    </div>
    
    <div class="stage-ratings">
        <p><strong>各环节评分</strong></p>
        <div class="stage-item">
            <span>上传体验</span>
            <div class="stage-stars" data-stage="upload">
                <span class="star" onclick="rateStage('upload', 1)">★</span>
                <span class="star" onclick="rateStage('upload', 2)">★</span>
                <span class="star" onclick="rateStage('upload', 3)">★</span>
                <span class="star" onclick="rateStage('upload', 4)">★</span>
                <span class="star" onclick="rateStage('upload', 5)">★</span>
            </div>
        </div>
        <div class="stage-item">
            <span>分析准确性</span>
            <div class="stage-stars" data-stage="parsing">
                <span class="star" onclick="rateStage('parsing', 1)">★</span>
                <span class="star" onclick="rateStage('parsing', 2)">★</span>
                <span class="star" onclick="rateStage('parsing', 3)">★</span>
                <span class="star" onclick="rateStage('parsing', 4)">★</span>
                <span class="star" onclick="rateStage('parsing', 5)">★</span>
            </div>
        </div>
        <div class="stage-item">
            <span>报告质量</span>
            <div class="stage-stars" data-stage="report">
                <span class="star" onclick="rateStage('report', 1)">★</span>
                <span class="star" onclick="rateStage('report', 2)">★</span>
                <span class="star" onclick="rateStage('report', 3)">★</span>
                <span class="star" onclick="rateStage('report', 4)">★</span>
                <span class="star" onclick="rateStage('report', 5)">★</span>
            </div>
        </div>
    </div>
    
    <div class="open-feedback">
        <p><strong>其他建议</strong></p>
        <textarea id="suggestion-text" placeholder="告诉我们做得好的地方，或需要改进的地方..." rows="4"></textarea>
    </div>
    
    <button class="submit-report-feedback" onclick="submitReportFeedback()">提交反馈</button>
    <div class="submit-confirm" id="submit-confirm" style="display:none;">
        <p>✅ 感谢您的反馈！</p>
    </div>
</div>
'''
        return html
    
    def generate_feedback_css(self) -> str:
        """生成反馈组件的CSS样式"""
        return '''
<style>
/* Feedback Component Styles */
.ddq-feedback {
    margin-top: 10px;
    padding: 10px;
    background: #f8f9fa;
    border-radius: 6px;
}

.feedback-btn {
    background: #fff;
    border: 1px solid #ddd;
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
}

.feedback-btn:hover {
    background: #f0f0f0;
}

.feedback-form {
    margin-top: 10px;
    padding: 15px;
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
}

.feedback-title {
    font-weight: 600;
    margin-bottom: 10px;
}

.feedback-options {
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
}

.option-btn {
    flex: 1;
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    cursor: pointer;
    background: #fff;
}

.option-btn.correct:hover {
    background: #d4edda;
    border-color: #28a745;
}

.option-btn.wrong:hover {
    background: #f8d7da;
    border-color: #dc3545;
}

.correction-form select,
.correction-form textarea {
    width: 100%;
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    margin-top: 5px;
}

.submit-btn {
    margin-top: 10px;
    padding: 8px 16px;
    background: #007bff;
    color: #fff;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

.submit-btn:hover {
    background: #0056b3;
}

/* Report Feedback Section */
.report-feedback-section {
    margin-top: 40px;
    padding: 30px;
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
    border-radius: 12px;
}

.report-feedback-section h3 {
    margin-bottom: 20px;
    color: #333;
}

.star-rating,
.stage-stars {
    display: flex;
    gap: 5px;
    font-size: 24px;
    color: #ddd;
    cursor: pointer;
}

.star-rating .star:hover,
.star-rating .star.active,
.stage-stars .star:hover,
.stage-stars .star.active {
    color: #ffc107;
}

.stage-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #e0e0e0;
}

.open-feedback textarea {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 6px;
    margin-top: 10px;
}

.submit-report-feedback {
    margin-top: 20px;
    padding: 12px 30px;
    background: #28a745;
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 16px;
}

.submit-report-feedback:hover {
    background: #218838;
}

.feedback-thanks,
.submit-confirm {
    margin-top: 15px;
    padding: 10px;
    background: #d4edda;
    border-radius: 4px;
    color: #155724;
}
</style>
'''
    
    def generate_feedback_js(self) -> str:
        """生成反馈组件的JavaScript"""
        return f'''
<script>
// Feedback System JavaScript
const ASSESSMENT_ID = "{self.assessment_id}";
const USER_ID = "{self.user_id}";

// DDQ Feedback Functions
function toggleFeedbackForm(ddqId) {{
    const form = document.getElementById('form-' + ddqId);
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}}

function submitFeedback(ddqId, type) {{
    if (type === 'correct') {{
        const feedbackData = {{
            assessment_id: ASSESSMENT_ID,
            user_id: USER_ID,
            item_feedback: [{{
                ddq_id: ddqId,
                feedback_type: 'general',
                is_correct: true
            }}]
        }};
        
        // 发送到服务器（实际实现中替换为真实API）
        console.log('提交正确反馈:', feedbackData);
        
        // 显示感谢信息
        document.getElementById('thanks-' + ddqId).style.display = 'block';
        document.getElementById('form-' + ddqId).style.display = 'none';
    }}
}}

function showCorrectionForm(ddqId) {{
    document.getElementById('correction-' + ddqId).style.display = 'block';
}}

function onCorrectionTypeChange(ddqId) {{
    const type = document.getElementById('type-' + ddqId).value;
    const fields = document.getElementById('correction-fields-' + ddqId);
    fields.style.display = type ? 'block' : 'none';
}}

function submitCorrection(ddqId) {{
    const type = document.getElementById('type-' + ddqId).value;
    const reason = document.getElementById('reason-' + ddqId).value;
    
    if (!type) {{
        alert('请选择问题类型');
        return;
    }}
    
    const feedbackData = {{
        assessment_id: ASSESSMENT_ID,
        user_id: USER_ID,
        item_feedback: [{{
            ddq_id: ddqId,
            feedback_type: type,
            is_correct: false,
            correction_reason: reason
        }}]
    }};
    
    // 发送到服务器
    console.log('提交修正反馈:', feedbackData);
    
    // 显示感谢信息
    document.getElementById('thanks-' + ddqId).style.display = 'block';
    document.getElementById('correction-' + ddqId).style.display = 'none';
}}

// Report Feedback Functions
let ratings = {{}};

function rate(category, value) {{
    ratings[category] = value;
    const stars = document.querySelectorAll('#' + category + '-rating .star');
    stars.forEach((star, index) => {{
        star.classList.toggle('active', index < value);
    }});
}}

function rateStage(stage, value) {{
    ratings['stage_' + stage] = value;
    const container = document.querySelector('.stage-stars[data-stage="' + stage + '"]');
    const stars = container.querySelectorAll('.star');
    stars.forEach((star, index) => {{
        star.classList.toggle('active', index < value);
    }});
}}

function submitReportFeedback() {{
    const suggestion = document.getElementById('suggestion-text').value;
    
    const feedbackData = {{
        assessment_id: ASSESSMENT_ID,
        user_id: USER_ID,
        overall_rating: {{ score: ratings.overall || 0 }},
        stage_ratings: {{
            upload_experience: ratings.stage_upload || 0,
            parsing_accuracy: ratings.stage_parsing || 0,
            report_quality: ratings.stage_report || 0
        }},
        open_feedback: {{
            other_comments: suggestion
        }}
    }};
    
    // 发送到服务器
    console.log('提交报告反馈:', feedbackData);
    
    // 显示确认信息
    document.getElementById('submit-confirm').style.display = 'block';
}}
</script>
'''
    
    def inject_into_report(self, report_html: str, feedback_points: list = None) -> str:
        """
        将反馈组件注入到HTML报告中
        
        Args:
            report_html: 原始HTML报告内容
            feedback_points: 需要添加反馈的DDQ ID列表
        """
        # 在</head>前添加CSS
        css = self.generate_feedback_css()
        report_html = report_html.replace('</head>', css + '</head>')
        
        # 在</body>前添加JS
        js = self.generate_feedback_js()
        report_html = report_html.replace('</body>', js + '</body>')
        
        # 在报告末尾添加整体反馈组件
        report_feedback = self.generate_report_end_feedback()
        report_html = report_html.replace('</body>', report_feedback + '</body>')
        
        return report_html


# 便捷函数
def add_feedback_to_report(report_html: str, assessment_id: str) -> str:
    """快速为报告添加反馈功能"""
    embedder = FeedbackEmbedder(assessment_id)
    return embedder.inject_into_report(report_html)
