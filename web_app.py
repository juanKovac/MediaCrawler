# -*- coding: utf-8 -*-
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

from flask import Flask, render_template, request, jsonify, send_file
import asyncio
import threading
import uuid
import os
import json
import time
from datetime import datetime
import sys
from typing import Dict, Any, Optional
import pandas as pd
import glob

# 导入原有的爬虫模块
import config
import db
from main import CrawlerFactory
from base.base_crawler import AbstractCrawler

app = Flask(__name__, template_folder='web_templates', static_folder='web_static')

# 存储任务状态的字典
tasks = {}

# 平台配置
PLATFORM_OPTIONS = {
    'xhs': '小红书',
    'dy': '抖音',
    'ks': '快手',
    'bili': '哔哩哔哩',
    'wb': '微博',
    'tieba': '百度贴吧',
    'zhihu': '知乎'
}

# 登录方式配置
LOGIN_TYPE_OPTIONS = {
    'qrcode': '二维码登录',
    'phone': '手机号登录',
    'cookie': 'Cookie登录'
}

# 爬取类型配置
CRAWLER_TYPE_OPTIONS = {
    'search': '关键词搜索',
    'detail': '帖子详情',
    'creator': '创作者主页'
}

# 数据保存方式配置
SAVE_DATA_OPTIONS = {
    'json': 'JSON文件',
    'csv': 'CSV文件',
    'sqlite': 'SQLite数据库',
    'db': 'MySQL数据库'
}

class TaskStatus:
    """任务状态类"""
    PENDING = 'pending'      # 等待中
    RUNNING = 'running'      # 运行中
    COMPLETED = 'completed'  # 已完成
    FAILED = 'failed'        # 失败
    STOPPED = 'stopped'      # 已停止

def run_crawler_task(task_id: str, crawler_config: Dict[str, Any]):
    """在后台线程中运行爬虫任务"""
    try:
        # 更新任务状态为运行中
        tasks[task_id]['status'] = TaskStatus.RUNNING
        tasks[task_id]['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tasks[task_id]['started_at'] = time.time()
        
        # 创建新的事件循环来运行异步爬虫任务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(execute_crawler_task(task_id, crawler_config))
        finally:
            loop.close()
        
    except Exception as e:
        # 更新任务状态为失败
        tasks[task_id]['status'] = TaskStatus.FAILED
        tasks[task_id]['error'] = str(e)
        tasks[task_id]['message'] = f'任务执行出错: {str(e)}'
        tasks[task_id]['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tasks[task_id]['completed_at'] = time.time()
        print(f"Task {task_id} failed with error: {e}")


async def execute_crawler_task(task_id: str, crawler_config: Dict[str, Any]):
    """执行爬虫任务的异步函数"""
    crawler: Optional[AbstractCrawler] = None
    
    try:
        # 设置配置参数
        config.PLATFORM = crawler_config['platform']
        config.LOGIN_TYPE = crawler_config['login_type']
        config.CRAWLER_TYPE = crawler_config['crawler_type']
        config.KEYWORDS = crawler_config['keywords']
        config.START_PAGE = crawler_config['start_page']
        config.ENABLE_GET_COMMENTS = crawler_config['get_comments']
        config.ENABLE_GET_SUB_COMMENTS = crawler_config['get_sub_comments']
        config.SAVE_DATA_OPTION = crawler_config['save_data_option']
        config.CRAWLER_MAX_NOTES_COUNT = crawler_config['max_notes_count']
        config.COOKIES = crawler_config.get('cookies', '')
        
        # 处理创作者模式的用户ID
        if crawler_config['crawler_type'] == 'creator' and crawler_config.get('creator_id'):
            # 将用户输入的创作者ID设置到配置中
            if crawler_config['platform'] == 'xhs':
                config.XHS_CREATOR_ID_LIST = [crawler_config['creator_id']]
        
        # 初始化数据库（如果需要）
        if config.SAVE_DATA_OPTION in ["db", "sqlite"]:
            await db.init_db()
        
        # 创建爬虫实例
        crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
        
        # 启动爬虫
        await crawler.start()
        
        # 获取输出文件列表
        output_files = get_output_files(crawler_config['platform'], task_id)
        
        # 更新任务状态为完成
        tasks[task_id]['status'] = TaskStatus.COMPLETED
        tasks[task_id]['message'] = '爬取任务完成！'
        tasks[task_id]['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tasks[task_id]['completed_at'] = time.time()
        tasks[task_id]['output_files'] = output_files
        
    except Exception as e:
        # 更新任务状态为失败
        tasks[task_id]['status'] = TaskStatus.FAILED
        tasks[task_id]['error'] = str(e)
        tasks[task_id]['message'] = '爬取任务失败！'
        tasks[task_id]['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tasks[task_id]['completed_at'] = time.time()
        raise
    
    finally:
        # 清理资源
        if crawler:
            try:
                # 如果爬虫有清理方法，调用它
                if hasattr(crawler, 'close'):
                    await crawler.close()
            except Exception as e:
                print(f"Error closing crawler: {e}")
        
        # 关闭数据库连接
        if config.SAVE_DATA_OPTION in ["db", "sqlite"]:
            try:
                await db.close()
            except Exception as e:
                print(f"Error closing database: {e}")


def get_output_files(platform: str, task_id: str) -> list:
    """获取任务生成的输出文件列表"""
    output_files = []
    data_dir = "data"
    
    if not os.path.exists(data_dir):
        return output_files
    
    # 查找与任务相关的文件
    for filename in os.listdir(data_dir):
        if platform in filename.lower():
            # 检查文件是否是在任务开始后创建的
            file_path = os.path.join(data_dir, filename)
            if os.path.isfile(file_path):
                file_mtime = os.path.getmtime(file_path)
                task_start_time = tasks.get(task_id, {}).get('started_at', 0)
                if file_mtime >= task_start_time:
                    output_files.append(filename)
    
    return output_files

@app.route('/')
def index():
    """主页"""
    return render_template('index.html', 
                         platforms=PLATFORM_OPTIONS,
                         login_types=LOGIN_TYPE_OPTIONS,
                         crawler_types=CRAWLER_TYPE_OPTIONS,
                         save_data_options=SAVE_DATA_OPTIONS)

@app.route('/start_task', methods=['POST'])
def start_task():
    """启动爬虫任务"""
    try:
        # 获取表单数据
        crawler_config = {
            'platform': request.form.get('platform', 'xhs'),
            'login_type': request.form.get('login_type', 'qrcode'),
            'crawler_type': request.form.get('crawler_type', 'search'),
            'keywords': request.form.get('keywords', ''),
            'creator_id': request.form.get('creator_id', ''),
            'start_page': int(request.form.get('start_page', 1)),
            'get_comments': request.form.get('get_comments') == 'on',
            'get_sub_comments': request.form.get('get_sub_comments') == 'on',
            'save_data_option': request.form.get('save_data_option', 'json'),
            'max_notes_count': int(request.form.get('max_notes_count', 20)),
            'cookies': request.form.get('cookies', '')
        }
        
        
        # 验证必要参数
        if crawler_config['crawler_type'] == 'search' and not crawler_config['keywords']:
            return jsonify({'success': False, 'message': '搜索模式下必须输入关键词！'})
        
        if crawler_config['crawler_type'] == 'creator' and not crawler_config['creator_id']:
            return jsonify({'success': False, 'message': '创作者模式下必须输入用户ID！'})
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务记录
        tasks[task_id] = {
            'id': task_id,
            'status': TaskStatus.PENDING,
            'config': crawler_config,
            'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'start_time': None,
            'end_time': None,
            'message': '任务已创建，等待执行...',
            'error': None
        }
        
        # 在后台线程中启动爬虫任务
        thread = threading.Thread(target=run_crawler_task, args=(task_id, crawler_config))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True, 
            'task_id': task_id,
            'message': '任务已启动，请查看任务状态页面获取进度信息。'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'启动任务失败: {str(e)}'})

@app.route('/task_status/<task_id>')
def get_task_status(task_id):
    """获取任务状态"""
    if task_id not in tasks:
        return jsonify({'success': False, 'message': '任务不存在'})
    
    task = tasks[task_id]
    return jsonify({
        'success': True,
        'task': task
    })

@app.route('/api/tasks/<task_id>')
def get_task_detail(task_id):
    """获取任务详情"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({'success': False, 'message': '任务不存在'})
    
    # 添加输出文件信息
    task_copy = task.copy()
    if 'output_files' not in task_copy and task_copy['status'] == TaskStatus.COMPLETED:
        task_copy['output_files'] = get_output_files(task_copy['config']['platform'], task_id)
    
    return jsonify({
        'success': True,
        'task': task_copy
    })

@app.route('/tasks')
def list_tasks():
    """任务列表页面"""
    return render_template('tasks.html', tasks=tasks)

@app.route('/api/tasks')
def api_list_tasks():
    """获取所有任务的API接口"""
    return jsonify({'success': True, 'tasks': list(tasks.values())})

@app.route('/stop_task/<task_id>', methods=['POST'])
def stop_task(task_id):
    """停止任务（注意：由于爬虫的异步特性，可能无法立即停止）"""
    if task_id not in tasks:
        return jsonify({'success': False, 'message': '任务不存在'})
    
    task = tasks[task_id]
    if task['status'] == TaskStatus.RUNNING:
        task['status'] = TaskStatus.STOPPED
        task['message'] = '任务已请求停止（可能需要等待当前操作完成）'
        task['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({'success': True, 'message': '停止请求已发送'})
    else:
        return jsonify({'success': False, 'message': '任务未在运行中'})

@app.route('/data')
def view_data():
    """数据查看页面"""
    return render_template('data.html')

@app.route('/creators')
def view_creators():
    """创作者数据查看页面"""
    return render_template('creators.html')

def safe_convert_to_text(value):
    """安全地将数值转换为文本格式，保持原始格式"""
    import pandas as pd
    if pd.isna(value) or value is None:
        return '0'
    return str(value)

def safe_convert_to_int(value):
    """安全地将数值转换为整数，处理包含中文单位的情况"""
    if pd.isna(value) or value is None:
        return 0
    
    # 如果已经是数字类型，直接返回
    if isinstance(value, (int, float)):
        return int(value)
    
    # 转换为字符串处理
    str_value = str(value).strip()
    
    # 如果是空字符串，返回0
    if not str_value:
        return 0
    
    # 尝试直接转换为整数
    try:
        return int(float(str_value))
    except ValueError:
        # 如果包含中文单位，返回0（或者可以选择保持原始字符串）
        return 0

@app.route('/api/creators')
def get_creators():
    """获取创作者列表API"""
    try:
        import pandas as pd
        import glob
        import json
        from datetime import datetime
        
        # 查找创作者详细信息文件
        creator_files = glob.glob('data/xhs/*_creator_creator_*.csv')
        if not creator_files:
            return jsonify({'success': True, 'creators': []})
        
        # 读取所有创作者文件并合并
        all_creator_data = []
        for file_path in creator_files:
            try:
                df = pd.read_csv(file_path)
                # 添加文件修改时间作为数据更新时间
                file_mtime = os.path.getmtime(file_path)
                df['data_update_time'] = file_mtime
                all_creator_data.append(df)
            except Exception as e:
                print(f"读取文件 {file_path} 失败: {e}")
                continue
        
        if not all_creator_data:
            return jsonify({'success': True, 'creators': []})
        
        # 合并所有数据
        creator_df = pd.concat(all_creator_data, ignore_index=True)
        
        # 按user_id分组，保留最新的数据（基于data_update_time）
        # 但确保所有创作者都能显示，即使他们不在最新文件中
        creator_df = creator_df.sort_values('data_update_time').groupby('user_id').tail(1).reset_index(drop=True)
        
        # 查找内容文件来获取笔记数量
        content_files = glob.glob('data/xhs/*_creator_contents_*.csv')
        note_counts = {}
        if content_files:
            all_content_data = []
            for file_path in content_files:
                try:
                    df = pd.read_csv(file_path)
                    all_content_data.append(df)
                except Exception as e:
                    continue
            
            if all_content_data:
                content_df = pd.concat(all_content_data, ignore_index=True)
                # 去重并统计笔记数量
                content_df = content_df.drop_duplicates(subset=['note_id'])
                note_counts = content_df.groupby('user_id').size().to_dict()
        
        creators = []
        for _, row in creator_df.iterrows():
            # 解析tag_list JSON字符串
            tag_info = {}
            try:
                if pd.notna(row.get('tag_list')) and row['tag_list'].strip():
                    tag_info = json.loads(row['tag_list'])
            except (json.JSONDecodeError, AttributeError):
                tag_info = {}
            
            # 格式化数据更新时间
            update_time = datetime.fromtimestamp(row['data_update_time']).strftime('%Y-%m-%d %H:%M:%S')
            
            # 安全处理可能包含NaN的字段
            def safe_get_value(value, default=''):
                if pd.isna(value) or value is None:
                    return default
                return str(value) if value != '' else default
            
            creators.append({
                'user_id': safe_get_value(row['user_id']),
                'nickname': safe_get_value(row['nickname']),
                'avatar': safe_get_value(row['avatar']),
                'desc': safe_get_value(row.get('desc', '')),  # 简介
                'ip_location': safe_get_value(row.get('ip_location', '')),
                'follows': safe_convert_to_int(row.get('follows', 0)),  # 关注数
                'fans': safe_convert_to_int(row.get('fans', 0)),  # 粉丝数
                'interaction': safe_convert_to_int(row.get('interaction', 0)),  # 总互动数
                'note_count': note_counts.get(row['user_id'], 0),  # 笔记数量
                'last_modify_ts': safe_convert_to_int(row.get('last_modify_ts', 0)),
                'data_update_time': update_time,  # 数据更新时间
                'gender': safe_get_value(row.get('gender', '')),  # 性别
                'tag_list': tag_info,  # 标签信息
                # 额外信息（年龄、地区、职业、学校等）
                'age': tag_info.get('info', ''),
                'location': tag_info.get('location', ''),
                'profession': tag_info.get('profession', ''),
                'college': tag_info.get('college', '')
            })
        
        # 按粉丝数排序
        creators.sort(key=lambda x: x['fans'], reverse=True)
        
        return jsonify({'success': True, 'creators': creators})
    except Exception as e:
        return jsonify({'success': False, 'message': f'加载创作者数据失败: {str(e)}'})

@app.route('/api/creator/<user_id>/notes')
def get_creator_notes(user_id):
    """获取指定创作者的笔记列表API"""
    try:
        import pandas as pd
        import glob
        
        # 获取排序参数
        sort_by = request.args.get('sort_by', 'time')  # 默认按时间排序
        sort_order = request.args.get('sort_order', 'desc')  # 默认降序
        
        # 查找所有小红书CSV文件
        csv_files = glob.glob('data/xhs/*_creator_contents_*.csv')
        if not csv_files:
            return jsonify({'success': True, 'notes': []})
        
        # 读取所有CSV文件并合并
        all_content_data = []
        for file_path in csv_files:
            try:
                df = pd.read_csv(file_path)
                all_content_data.append(df)
            except Exception as e:
                print(f"读取文件 {file_path} 失败: {e}")
                continue
        
        if not all_content_data:
            return jsonify({'success': True, 'notes': []})
        
        # 合并所有数据
        df = pd.concat(all_content_data, ignore_index=True)
        
        # 去重，保留每个note_id的最新数据
        df = df.drop_duplicates(subset=['note_id'], keep='last')
        
        # 筛选指定创作者的笔记
        user_notes = df[df['user_id'] == user_id].copy()
        
        # 处理排序字段的数据类型转换
        def convert_count_to_number(value):
            """将包含中文单位的数值转换为数字用于排序"""
            if pd.isna(value) or value == '':
                return 0
            
            str_value = str(value)
            if '万' in str_value:
                try:
                    return float(str_value.replace('万', '')) * 10000
                except:
                    return 0
            elif '千' in str_value:
                try:
                    return float(str_value.replace('千', '')) * 1000
                except:
                    return 0
            else:
                try:
                    return float(str_value)
                except:
                    return 0
        
        # 根据排序字段进行数据处理
        if sort_by in ['liked_count', 'collected_count', 'comment_count', 'share_count']:
            # 为数值字段创建临时排序列，直接转换为数值类型
            user_notes[f'{sort_by}_numeric'] = pd.to_numeric(user_notes[sort_by], errors='coerce').fillna(0)
            sort_column = f'{sort_by}_numeric'
        elif sort_by == 'time':
            # 时间字段转换为数值类型进行排序
            user_notes['time_numeric'] = pd.to_numeric(user_notes['time'], errors='coerce').fillna(0)
            sort_column = 'time_numeric'
        else:
            sort_column = sort_by
        
        # 执行排序
        ascending = (sort_order == 'asc')
        if sort_column in user_notes.columns:
            user_notes = user_notes.sort_values(sort_column, ascending=ascending)
        else:
            # 如果排序字段不存在，默认按时间排序
            user_notes['time_numeric'] = pd.to_numeric(user_notes['time'], errors='coerce').fillna(0)
            user_notes = user_notes.sort_values('time_numeric', ascending=False)
        
        notes = []
        for _, row in user_notes.iterrows():
            notes.append({
                'note_id': row['note_id'],
                'title': row['title'] if pd.notna(row['title']) else '',
                'desc': row['desc'] if pd.notna(row['desc']) else '',
                'type': row['type'] if pd.notna(row['type']) else '',
                'video_url': row['video_url'] if pd.notna(row['video_url']) else '',
                'time': str(int(row['time'])) if pd.notna(row['time']) else '',
                'last_update_time': str(int(row['last_update_time'])) if pd.notna(row['last_update_time']) else '',
                'liked_count': safe_convert_to_text(row['liked_count']),
                'collected_count': safe_convert_to_text(row['collected_count']),
                'comment_count': safe_convert_to_text(row['comment_count']),
                'share_count': safe_convert_to_text(row['share_count']),
                'image_list': row['image_list'] if pd.notna(row['image_list']) else '',
                'tag_list': row['tag_list'] if pd.notna(row['tag_list']) else '',
                'note_url': row['note_url'] if pd.notna(row['note_url']) else '',
                'ip_location': row['ip_location'] if pd.notna(row['ip_location']) else ''
            })
        
        return jsonify({'success': True, 'notes': notes})
    except Exception as e:
        return jsonify({'success': False, 'message': f'加载笔记数据失败: {str(e)}'})

@app.route('/api/data_files')
def list_data_files():
    """获取数据文件列表"""
    try:
        data_dir = 'data'
        if not os.path.exists(data_dir):
            return jsonify({'success': True, 'files': []})
        
        files = []
        for filename in os.listdir(data_dir):
            if filename.endswith(('.json', '.csv')):
                filepath = os.path.join(data_dir, filename)
                stat = os.stat(filepath)
                files.append({
                    'name': filename,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/data/files')
def get_data_files():
    """获取数据文件列表"""
    try:
        data_dir = 'data'
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            return jsonify({'success': True, 'files': []})
        
        files = []
        for filename in os.listdir(data_dir):
            file_path = os.path.join(data_dir, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    'name': filename,
                    'size': stat.st_size,
                    'modified_time': stat.st_mtime
                })
        
        # 按修改时间倒序排列
        files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/download/<filename>')
def download_file(filename):
    """下载数据文件"""
    try:
        # 安全检查：防止路径遍历攻击
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'success': False, 'message': '非法文件名'}), 400
        
        file_path = os.path.join('data', filename)
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    # 确保必要的目录存在
    os.makedirs('web_templates', exist_ok=True)
    os.makedirs('web_static', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    print("\n" + "="*50)
    print("🚀 MediaCrawler Web 界面已启动！")
    print("📱 请在浏览器中访问: http://localhost:5000")
    print("💡 使用Web界面可以更方便地配置和管理爬虫任务")
    print("="*50 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)