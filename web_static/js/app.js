// MediaCrawler Web 应用 JavaScript 功能

// 全局变量
let currentTaskId = null;
let refreshInterval = null;
let taskListInterval = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// 初始化应用
function initializeApp() {
    // 绑定表单提交事件
    const crawlerForm = document.getElementById('crawlerForm');
    if (crawlerForm) {
        crawlerForm.addEventListener('submit', handleFormSubmit);
    }

    // 绑定高级设置切换
    const advancedToggle = document.getElementById('advancedToggle');
    if (advancedToggle) {
        advancedToggle.addEventListener('click', toggleAdvancedSettings);
    }

    // 根据页面类型初始化不同功能
    const currentPage = getCurrentPage();
    switch (currentPage) {
        case 'tasks':
            initializeTasksPage();
            break;
        case 'data':
            initializeDataPage();
            break;
        default:
            initializeHomePage();
    }

    // 初始化工具提示
    initializeTooltips();
}

// 获取当前页面类型
function getCurrentPage() {
    const path = window.location.pathname;
    if (path.includes('tasks')) return 'tasks';
    if (path.includes('data')) return 'data';
    return 'home';
}

// 初始化首页
function initializeHomePage() {
    // 绑定平台选择变化事件
    const platformRadios = document.querySelectorAll('input[name="platform"]');
    platformRadios.forEach(radio => {
        radio.addEventListener('change', handlePlatformChange);
    });

    // 绑定爬取类型变化事件
    const crawlerTypeRadios = document.querySelectorAll('input[name="crawler_type"]');
    crawlerTypeRadios.forEach(radio => {
        radio.addEventListener('change', handleCrawlerTypeChange);
    });

    // 初始化表单验证
    initializeFormValidation();
}

// 初始化任务页面
function initializeTasksPage() {
    loadTaskList();
    // 每5秒刷新任务列表
    taskListInterval = setInterval(loadTaskList, 5000);
}

// 初始化数据页面
function initializeDataPage() {
    loadDataFiles();
}

// 处理表单提交
function handleFormSubmit(event) {
    event.preventDefault();
    
    if (!validateForm()) {
        return;
    }

    const formData = new FormData(event.target);
    const submitBtn = document.getElementById('startBtn');
    
    // 显示加载状态
    setButtonLoading(submitBtn, true);
    
    fetch('/start_task', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('任务启动成功！', 'success');
            currentTaskId = data.task_id;
            // 3秒后跳转到任务页面
            setTimeout(() => {
                window.location.href = '/tasks';
            }, 3000);
        } else {
            showMessage('任务启动失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('网络错误，请重试', 'error');
    })
    .finally(() => {
        setButtonLoading(submitBtn, false);
    });
}

// 表单验证
function validateForm() {
    // 获取选中的平台radio按钮值
    const platformRadio = document.querySelector('input[name="platform"]:checked');
    const platform = platformRadio ? platformRadio.value : '';
    
    // 获取选中的爬取类型radio按钮值
    const crawlerTypeRadio = document.querySelector('input[name="crawler_type"]:checked');
    const crawlerType = crawlerTypeRadio ? crawlerTypeRadio.value : '';
    
    const keywords = document.getElementById('keywords').value.trim();
    const creatorId = document.getElementById('creator_id').value.trim();
    
    // 验证平台选择
    if (!platform) {
        showMessage('请选择爬取平台', 'error');
        return false;
    }
    
    // 验证爬取类型选择
    if (!crawlerType) {
        showMessage('请选择爬取类型', 'error');
        return false;
    }
    
    // 验证关键词（搜索模式下必填）
    if (crawlerType === 'search' && !keywords) {
        showMessage('搜索模式下必须输入关键词', 'error');
        document.getElementById('keywords').focus();
        return false;
    }
    
    // 验证创作者ID（创作者模式下必填）
    if (crawlerType === 'creator' && !creatorId) {
        showMessage('创作者模式下必须输入用户ID', 'error');
        document.getElementById('creator_id').focus();
        return false;
    }
    
    return true;
}

// 初始化表单验证
function initializeFormValidation() {
    const inputs = document.querySelectorAll('.form-control, .form-select');
    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', clearFieldError);
    });
}

// 验证单个字段
function validateField(event) {
    const field = event.target;
    const value = field.value.trim();
    
    // 清除之前的错误状态
    clearFieldError(event);
    
    // 验证必填字段
    if (field.hasAttribute('required') && !value) {
        setFieldError(field, '此字段为必填项');
        return false;
    }
    
    // 验证关键词字段
    if (field.id === 'keywords') {
        const crawlerType = document.getElementById('crawler_type').value;
        if (crawlerType === 'search' && !value) {
            setFieldError(field, '搜索模式下必须输入关键词');
            return false;
        }
    }
    
    return true;
}

// 清除字段错误状态
function clearFieldError(event) {
    const field = event.target;
    field.classList.remove('is-invalid');
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.remove();
    }
}

// 设置字段错误状态
function setFieldError(field, message) {
    field.classList.add('is-invalid');
    
    // 移除旧的错误消息
    const oldFeedback = field.parentNode.querySelector('.invalid-feedback');
    if (oldFeedback) {
        oldFeedback.remove();
    }
    
    // 添加新的错误消息
    const feedback = document.createElement('div');
    feedback.className = 'invalid-feedback';
    feedback.textContent = message;
    field.parentNode.appendChild(feedback);
}

// 处理平台选择变化
function handlePlatformChange(event) {
    const platform = event.target.value;
    // 可以根据平台调整其他选项
    console.log('Platform changed to:', platform);
}

// 处理爬取类型变化
function handleCrawlerTypeChange(event) {
    const crawlerType = event.target.value;
    const keywordsGroup = document.getElementById('keywords_group');
    const keywordsInput = document.getElementById('keywords');
    const creatorIdGroup = document.getElementById('creatorIdGroup');
    const creatorIdInput = document.getElementById('creator_id');
    
    // 添加空值检查，防止访问null元素的属性
    if (!keywordsGroup || !keywordsInput || !creatorIdGroup || !creatorIdInput) {
        console.error('Required DOM elements not found:', {
            keywordsGroup: !!keywordsGroup,
            keywordsInput: !!keywordsInput,
            creatorIdGroup: !!creatorIdGroup,
            creatorIdInput: !!creatorIdInput
        });
        return;
    }
    
    if (crawlerType === 'search') {
        // 搜索模式：显示关键词输入框，隐藏用户ID输入框
        keywordsGroup.style.display = 'block';
        keywordsInput.setAttribute('required', 'required');
        creatorIdGroup.style.display = 'none';
        creatorIdInput.removeAttribute('required');
        creatorIdInput.value = '';
    } else if (crawlerType === 'creator') {
        // 创作者模式：显示用户ID输入框，隐藏关键词输入框
        keywordsGroup.style.display = 'none';
        keywordsInput.removeAttribute('required');
        keywordsInput.value = '';
        creatorIdGroup.style.display = 'block';
        creatorIdInput.setAttribute('required', 'required');
    } else {
        // 其他模式：隐藏两个输入框
        keywordsGroup.style.display = 'none';
        keywordsInput.removeAttribute('required');
        keywordsInput.value = '';
        creatorIdGroup.style.display = 'none';
        creatorIdInput.removeAttribute('required');
        creatorIdInput.value = '';
    }
}

// 切换高级设置
function toggleAdvancedSettings() {
    const advancedSettings = document.getElementById('advancedSettings');
    const toggleIcon = document.querySelector('#advancedToggle i');
    
    if (advancedSettings.style.display === 'none' || !advancedSettings.style.display) {
        advancedSettings.style.display = 'block';
        toggleIcon.className = 'fas fa-chevron-up';
    } else {
        advancedSettings.style.display = 'none';
        toggleIcon.className = 'fas fa-chevron-down';
    }
}

// 加载任务列表
function loadTaskList() {
    fetch('/api/tasks')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderTaskList(data.tasks);
            } else {
                showMessage('加载任务列表失败', 'error');
            }
        })
        .catch(error => {
            console.error('Error loading tasks:', error);
        });
}

// 渲染任务列表
function renderTaskList(tasks) {
    const taskList = document.getElementById('taskList');
    if (!taskList) return;
    
    if (tasks.length === 0) {
        taskList.innerHTML = `
            <div class="col-12">
                <div class="alert alert-info text-center">
                    <i class="fas fa-info-circle me-2"></i>
                    暂无任务记录
                </div>
            </div>
        `;
        return;
    }
    
    taskList.innerHTML = tasks.map(task => `
        <div class="col-md-6 col-lg-4 mb-4">
            <div class="card task-card h-100" onclick="showTaskDetails('${task.id}')">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <h6 class="card-title mb-0">
                            <i class="fas fa-tasks me-2"></i>
                            任务 ${task.id.substring(0, 8)}
                        </h6>
                        <span class="badge status-${task.status}">
                            ${getStatusIcon(task.status)} ${getStatusText(task.status)}
                        </span>
                    </div>
                    
                    <div class="mb-2">
                        <small class="text-muted">
                            <i class="fas fa-globe me-1"></i>
                            平台: ${getPlatformText(task.platform)}
                        </small>
                    </div>
                    
                    <div class="mb-2">
                        <small class="text-muted">
                            <i class="fas fa-search me-1"></i>
                            类型: ${getCrawlerTypeText(task.crawler_type)}
                        </small>
                    </div>
                    
                    ${task.keywords ? `
                        <div class="mb-2">
                            <small class="text-muted">
                                <i class="fas fa-key me-1"></i>
                                关键词: ${task.keywords}
                            </small>
                        </div>
                    ` : ''}
                    
                    <div class="mb-3">
                        <small class="text-muted">
                            <i class="fas fa-clock me-1"></i>
                            创建时间: ${formatDateTime(task.created_at)}
                        </small>
                    </div>
                    
                    <div class="d-flex gap-2">
                        ${task.status === 'running' ? `
                            <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); stopTask('${task.id}')">
                                <i class="fas fa-stop me-1"></i>停止
                            </button>
                        ` : ''}
                        
                        <button class="btn btn-sm btn-info" onclick="event.stopPropagation(); showTaskDetails('${task.id}')">
                            <i class="fas fa-info-circle me-1"></i>详情
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

// 显示任务详情
function showTaskDetails(taskId) {
    fetch(`/api/tasks/${taskId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderTaskDetailsModal(data.task);
            } else {
                showMessage('获取任务详情失败', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('网络错误', 'error');
        });
}

// 渲染任务详情模态框
function renderTaskDetailsModal(task) {
    const modalHtml = `
        <div class="modal fade" id="taskDetailsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-tasks me-2"></i>
                            任务详情 - ${task.id.substring(0, 8)}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6><i class="fas fa-info-circle me-2"></i>基本信息</h6>
                                <table class="table table-sm">
                                    <tr><td>任务ID:</td><td>${task.id}</td></tr>
                                    <tr><td>状态:</td><td><span class="badge status-${task.status}">${getStatusText(task.status)}</span></td></tr>
                                    <tr><td>平台:</td><td>${getPlatformText(task.platform)}</td></tr>
                                    <tr><td>类型:</td><td>${getCrawlerTypeText(task.crawler_type)}</td></tr>
                                    ${task.keywords ? `<tr><td>关键词:</td><td>${task.keywords}</td></tr>` : ''}
                                    <tr><td>创建时间:</td><td>${formatDateTime(task.created_at)}</td></tr>
                                    ${task.completed_at ? `<tr><td>完成时间:</td><td>${formatDateTime(task.completed_at)}</td></tr>` : ''}
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h6><i class="fas fa-cog me-2"></i>配置参数</h6>
                                <table class="table table-sm">
                                    <tr><td>起始页码:</td><td>${task.start_page || 1}</td></tr>
                                    <tr><td>最大数量:</td><td>${task.max_count || '不限制'}</td></tr>
                                    <tr><td>数据保存:</td><td>${getSaveOptionText(task.save_data_option)}</td></tr>
                                    <tr><td>爬取评论:</td><td>${task.get_comment ? '是' : '否'}</td></tr>
                                    <tr><td>爬取二级评论:</td><td>${task.get_sub_comment ? '是' : '否'}</td></tr>
                                </table>
                            </div>
                        </div>
                        
                        ${task.error_message ? `
                            <div class="mt-3">
                                <h6><i class="fas fa-exclamation-triangle me-2 text-danger"></i>错误信息</h6>
                                <div class="alert alert-danger">
                                    <pre class="mb-0">${task.error_message}</pre>
                                </div>
                            </div>
                        ` : ''}
                        
                        ${task.output_files && task.output_files.length > 0 ? `
                            <div class="mt-3">
                                <h6><i class="fas fa-file me-2"></i>输出文件</h6>
                                <div class="list-group">
                                    ${task.output_files.map(file => `
                                        <a href="/download/${encodeURIComponent(file)}" class="list-group-item list-group-item-action">
                                            <i class="fas fa-download me-2"></i>${file}
                                        </a>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        ${task.status === 'running' ? `
                            <button type="button" class="btn btn-danger" onclick="stopTask('${task.id}')">
                                <i class="fas fa-stop me-1"></i>停止任务
                            </button>
                        ` : ''}
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除旧的模态框
    const oldModal = document.getElementById('taskDetailsModal');
    if (oldModal) {
        oldModal.remove();
    }
    
    // 添加新的模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('taskDetailsModal'));
    modal.show();
}

// 停止任务
function stopTask(taskId) {
    if (!confirm('确定要停止这个任务吗？')) {
        return;
    }
    
    fetch(`/api/tasks/${taskId}/stop`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('任务已停止', 'success');
            loadTaskList(); // 刷新任务列表
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('taskDetailsModal'));
            if (modal) {
                modal.hide();
            }
        } else {
            showMessage('停止任务失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('网络错误', 'error');
    });
}

// 加载数据文件列表
function loadDataFiles() {
    fetch('/api/data/files')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderDataFileList(data.files);
            } else {
                showMessage('加载文件列表失败', 'error');
            }
        })
        .catch(error => {
            console.error('Error loading files:', error);
        });
}

// 渲染数据文件列表
function renderDataFileList(files) {
    const fileList = document.getElementById('fileList');
    if (!fileList) return;
    
    if (files.length === 0) {
        fileList.innerHTML = `
            <div class="alert alert-info text-center">
                <i class="fas fa-info-circle me-2"></i>
                暂无数据文件
            </div>
        `;
        return;
    }
    
    fileList.innerHTML = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th><i class="fas fa-file me-2"></i>文件名</th>
                        <th><i class="fas fa-weight me-2"></i>大小</th>
                        <th><i class="fas fa-clock me-2"></i>修改时间</th>
                        <th><i class="fas fa-cog me-2"></i>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${files.map(file => `
                        <tr>
                            <td>
                                <i class="fas fa-file-${getFileIcon(file.name)} file-icon ${getFileType(file.name)}"></i>
                                ${file.name}
                            </td>
                            <td>${formatFileSize(file.size)}</td>
                            <td>${formatDateTime(file.modified_time)}</td>
                            <td>
                                <div class="btn-group btn-group-sm">
                                    <button class="btn btn-outline-info" onclick="previewFile('${file.name}')" title="预览">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                    <a href="/download/${encodeURIComponent(file.name)}" class="btn btn-outline-success" title="下载">
                                        <i class="fas fa-download"></i>
                                    </a>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// 预览文件
function previewFile(filename) {
    fetch(`/api/data/preview/${encodeURIComponent(filename)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showFilePreviewModal(filename, data.content, data.file_type);
            } else {
                showMessage('预览文件失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('网络错误', 'error');
        });
}

// 显示文件预览模态框
function showFilePreviewModal(filename, content, fileType) {
    const modalHtml = `
        <div class="modal fade" id="filePreviewModal" tabindex="-1">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-file-${getFileIcon(filename)} me-2"></i>
                            文件预览 - ${filename}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <pre><code class="language-${fileType}">${escapeHtml(content)}</code></pre>
                    </div>
                    <div class="modal-footer">
                        <a href="/download/${encodeURIComponent(filename)}" class="btn btn-success">
                            <i class="fas fa-download me-1"></i>下载文件
                        </a>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除旧的模态框
    const oldModal = document.getElementById('filePreviewModal');
    if (oldModal) {
        oldModal.remove();
    }
    
    // 添加新的模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('filePreviewModal'));
    modal.show();
}

// 工具函数
function getStatusIcon(status) {
    const icons = {
        'pending': 'fas fa-clock',
        'running': 'fas fa-spinner fa-spin',
        'completed': 'fas fa-check',
        'failed': 'fas fa-times',
        'stopped': 'fas fa-stop'
    };
    return `<i class="${icons[status] || 'fas fa-question'}"></i>`;
}

function getStatusText(status) {
    const texts = {
        'pending': '等待中',
        'running': '运行中',
        'completed': '已完成',
        'failed': '失败',
        'stopped': '已停止'
    };
    return texts[status] || '未知';
}

function getPlatformText(platform) {
    const platforms = {
        'xhs': '小红书',
        'dy': '抖音',
        'ks': '快手',
        'bili': '哔哩哔哩',
        'wb': '微博'
    };
    return platforms[platform] || platform;
}

function getCrawlerTypeText(type) {
    const types = {
        'search': '关键词搜索',
        'detail': '指定详情',
        'creator': '博主主页'
    };
    return types[type] || type;
}

function getSaveOptionText(option) {
    const options = {
        'json': 'JSON格式',
        'csv': 'CSV格式',
        'db': '数据库',
        'all': '全部格式'
    };
    return options[option] || option;
}

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    if (ext === 'json') return 'code';
    if (ext === 'csv') return 'table';
    if (ext === 'db') return 'database';
    return 'alt';
}

function getFileType(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    return ext;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDateTime(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('zh-CN');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function setButtonLoading(button, loading) {
    if (loading) {
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>处理中...';
    } else {
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-play me-2"></i>开始爬取';
    }
}

function showMessage(message, type = 'info') {
    // 移除旧的消息
    const oldMessage = document.querySelector('.alert-message');
    if (oldMessage) {
        oldMessage.remove();
    }
    
    // 创建新的消息
    const alertClass = type === 'error' ? 'alert-danger' : 
                      type === 'success' ? 'alert-success' : 
                      type === 'warning' ? 'alert-warning' : 'alert-info';
    
    const icon = type === 'error' ? 'fas fa-exclamation-triangle' :
                type === 'success' ? 'fas fa-check-circle' :
                type === 'warning' ? 'fas fa-exclamation-circle' : 'fas fa-info-circle';
    
    const messageHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show alert-message" role="alert">
            <i class="${icon} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // 插入到页面顶部
    const container = document.querySelector('.container');
    if (container) {
        container.insertAdjacentHTML('afterbegin', messageHtml);
        
        // 3秒后自动消失
        setTimeout(() => {
            const alert = document.querySelector('.alert-message');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 3000);
    }
}

function initializeTooltips() {
    // 初始化Bootstrap工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// 页面卸载时清理定时器
window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    if (taskListInterval) {
        clearInterval(taskListInterval);
    }
});