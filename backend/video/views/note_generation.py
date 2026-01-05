"""
AI 笔记生成服务 - 参考 Video2Note 项目
使用 LLM 分析字幕内容，获取关键帧截图生成结构化笔记
"""

import os
import re
import json
import uuid
import tempfile
from typing import List, Dict, Optional
from pathlib import Path

from django.http import JsonResponse
from django.views import View
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

import cv2
import numpy as np
from openai import OpenAI

from ..models import Video


def get_system_prompt(style: str = "professional") -> str:
    """获取 LLM System Prompt"""
    style_descriptions = {
        "professional": "专业严谨的技术文档风格，语言精炼准确",
        "blog": "轻松易读的博客风格，适当使用比喻和例子",
        "tutorial": "循序渐进的教程风格，详细解释每个概念"
    }

    style_desc = style_descriptions.get(style, style_descriptions["professional"])

    return f"""# 角色
你是一位极其注重细节的视频拉片员和技术文档工程师。你的目标是将视频字幕转化为一份**"逐帧级"的图文实录**。

# 核心要求（关键痛点）
用户反馈之前的转换丢失了太多视觉细节。请注意：视频中往往一两句话画面就会变化。你的任务是捕捉每一个视觉变化点，绝对不要将多个不同的画面动作合并成一个长段落。截图占位符的频率要高，宁多勿少。

# 任务
根据提供的字幕文本，生成一篇流式图文教程。

# 处理规则
1. **高频插图策略**：
   - **动作即截图**：只要讲者执行了一个操作（点击、拖拽、连线），必须插入截图
   - **变化即截图**：只要画面发生了改变（参数变化、生成结果对比、局部特写），必须插入截图
   - **一事一图**：如果一句话里包含两个动作（"点击这里，然后选择那个"），请拆分为两行，并分别插入两个截图占位符

2. **微步骤结构**：
   - 不要写大段落，使用短句或微段落（2-3行以内）
   - 每个操作步骤独立成段

3. **内容清洗与修正**：
   - **术语修正**：将字幕中的错别字修正为专业术语
   - **去口语**：保留技术细节，去掉"哎呦喂"、"那么"、"那个"等废话
   - 完整保留原始视频中的所有关键信息、技术参数和核心观点

4. **截图时间点格式**：
   - 在正文中使用 `[HH:MM:SS]` 格式插入截图占位符
   - 时间戳必须来自原始字幕，保证顺序正确
   - 频率要高：每1-3句话至少一个截图点

# 输出风格
{style_desc}

# 输出格式
严格按照以下 JSON 格式输出，不要包含任何其他内容：
[
  {{
    "timestamp": "00:01:23",
    "title": "章节标题（简洁有力，5-15字）",
    "content": "章节正文内容（Markdown格式）。正文应为纯粹的技术文章，不要出现'关键帧'、'画面描述'、'截图'等元信息词汇。在需要配图的位置仅插入时间戳标记：[HH:MM:SS]，系统会自动替换为对应的视频截图。"
  }}
]

# 注意事项
- 确保输出是合法的JSON数组
- 时间戳格式必须为 HH:MM:SS
- 每个章节都必须有 timestamp、title、content 三个字段
"""


def is_blurry(image: np.ndarray, threshold: float = 100.0) -> bool:
    """
    检测图片是否模糊（使用拉普拉斯方差）
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return variance < threshold


def extract_frame(
    video_path: str,
    timestamp_seconds: float,
    output_dir: str,
    max_retries: int = 3,
    retry_offset: float = 0.5,
    blur_threshold: float = 100.0
) -> str:
    """
    从视频中提取指定时间戳的帧
    如果帧模糊，会自动向后偏移重试
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError(f"无法打开视频文件: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    # 确保时间戳在视频范围内
    current_time = min(timestamp_seconds, duration - 0.1)
    current_time = max(0, current_time)

    best_frame = None
    best_variance = 0

    for attempt in range(max_retries):
        # 计算帧位置
        frame_pos = int(current_time * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)

        ret, frame = cap.read()
        if not ret:
            current_time += retry_offset
            continue

        # 检查模糊度
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        variance = cv2.Laplacian(gray, cv2.CV_64F).var()

        # 保存最清晰的帧
        if variance > best_variance:
            best_variance = variance
            best_frame = frame.copy()

        # 如果不模糊，直接使用
        if variance >= blur_threshold:
            break

        # 向后偏移重试
        current_time += retry_offset

    cap.release()

    if best_frame is None:
        raise ValueError(f"无法从视频中提取帧: timestamp={timestamp_seconds}")

    # 保存图片
    os.makedirs(output_dir, exist_ok=True)
    filename = f"frame_{uuid.uuid4().hex[:8]}.jpg"
    output_path = os.path.join(output_dir, filename)

    # 使用较高质量保存
    cv2.imwrite(output_path, best_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])

    return output_path


def timestamp_to_seconds(timestamp: str) -> float:
    """将 HH:MM:SS 或 MM:SS 格式的时间戳转换为秒数"""
    parts = timestamp.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    elif len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    else:
        return float(timestamp)


def analyze_subtitles(
    subtitle_text: str,
    api_key: str,
    style: str = "professional",
    base_url: str = None,
    model: str = "gpt-4o-mini"
) -> List[Dict]:
    """
    使用 LLM 分析字幕内容，生成结构化笔记
    """
    client = OpenAI(
        api_key=api_key,
        base_url=base_url if base_url else "https://api.openai.com/v1"
    )

    system_prompt = get_system_prompt(style)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请分析以下字幕内容并生成结构化笔记：\n\n{subtitle_text}"}
            ],
            temperature=0.3,
            max_tokens=4096
        )

        content = response.choices[0].message.content.strip()
        
        # 尝试提取JSON部分
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        
        result = json.loads(content)
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        print(f"原始内容: {content}")
        return []
    except Exception as e:
        print(f"LLM分析错误: {e}")
        raise


@method_decorator(csrf_exempt, name='dispatch')
class NoteGenerationView(View):
    """
    AI笔记生成API
    POST /api/notes/generate/<video_id>
    """
    
    def post(self, request, video_id):
        """生成AI笔记"""
        try:
            # 获取视频信息
            try:
                video = Video.objects.get(pk=video_id)
            except Video.DoesNotExist:
                return JsonResponse({'success': False, 'error': '视频不存在'}, status=404)
            
            # 解析请求参数
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                data = {}
            
            # 只需要获取style，LLM配置从设置页读取
            style = data.get('style', 'professional')
            
            # 从配置文件获取LLM设置
            from .set_setting import load_all_settings
            settings_data = load_all_settings()
            cfg = settings_data.get('DEFAULT', {})
            
            # 获取选中的模型提供商
            selected_provider = cfg.get('selected_model_provider', 'deepseek')
            
            # 根据提供商获取API配置
            if selected_provider == 'deepseek':
                api_key = cfg.get('deepseek_api_key', '')
                base_url = cfg.get('deepseek_base_url', 'https://api.deepseek.com')
                model = 'deepseek-chat'
            elif selected_provider == 'openai':
                api_key = cfg.get('openai_api_key', '')
                base_url = cfg.get('openai_base_url', 'https://api.openai.com/v1')
                model = 'gpt-4o'
            elif selected_provider == 'glm':
                api_key = cfg.get('glm_api_key', '')
                base_url = cfg.get('glm_base_url', 'https://open.bigmodel.cn/api/paas/v4')
                model = 'glm-4-plus'
            elif selected_provider == 'qwen':
                api_key = cfg.get('qwen_api_key', '')
                base_url = cfg.get('qwen_base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
                model = 'qwen-plus'
            else:
                api_key = cfg.get('deepseek_api_key', '')
                base_url = cfg.get('deepseek_base_url', 'https://api.deepseek.com')
                model = 'deepseek-chat'
            
            if not api_key:
                return JsonResponse({
                    'success': False, 
                    'error': f'未配置{selected_provider}的API Key，请在设置页面配置大模型'
                }, status=400)
            
            # 获取字幕内容
            subtitle_text = self._get_subtitle_text(video)
            if not subtitle_text:
                return JsonResponse({'success': False, 'error': '未找到字幕文件'}, status=400)
            
            # 获取视频文件路径
            video_path = self._get_video_path(video)
            if not video_path or not os.path.exists(video_path):
                return JsonResponse({'success': False, 'error': '未找到视频文件'}, status=400)
            
            # 使用LLM分析字幕
            llm_results = analyze_subtitles(
                subtitle_text=subtitle_text,
                api_key=api_key,
                style=style,
                base_url=base_url,
                model=model
            )
            
            if not llm_results:
                return JsonResponse({'success': False, 'error': 'LLM分析失败'}, status=500)
            
            # 创建输出目录
            output_dir = os.path.join(
                settings.MEDIA_ROOT, 
                'note_frames', 
                f'video_{video_id}'
            )
            os.makedirs(output_dir, exist_ok=True)
            
            # 提取关键帧并构建笔记数据
            notes = []
            frame_cache = {}
            
            for item in llm_results:
                timestamp = item.get("timestamp", "00:00:00")
                seconds = timestamp_to_seconds(timestamp)
                content = item.get("content", "")
                
                # 提取章节主图
                main_image_path = self._get_frame_for_timestamp(
                    video_path, timestamp, output_dir, frame_cache
                )
                
                # 处理content中的时间戳标记，替换为图片
                processed_content = self._process_content_timestamps(
                    content, video_path, output_dir, frame_cache
                )
                
                # 构建相对URL
                main_image_url = None
                if main_image_path and os.path.exists(main_image_path):
                    relative_path = os.path.relpath(main_image_path, settings.MEDIA_ROOT)
                    main_image_url = f"/media/{relative_path.replace(os.sep, '/')}"
                
                note = {
                    "id": uuid.uuid4().hex,
                    "timestamp": timestamp,
                    "seconds": seconds,
                    "title": item.get("title", ""),
                    "content": processed_content,
                    "imagePath": main_image_url,
                    "isEdited": False
                }
                notes.append(note)
            
            return JsonResponse({
                'success': True,
                'data': notes,
                'message': f'成功生成 {len(notes)} 个笔记章节'
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    def _get_subtitle_text(self, video) -> str:
        """获取视频的字幕文本"""
        # 尝试获取SRT文件
        srt_dir = os.path.join(settings.MEDIA_ROOT, 'saved_srt')
        
        # 可能的基础文件名
        base_names = []
        
        # 1. 使用视频ID
        base_names.append(str(video.id))
        
        # 2. 使用视频URL（去掉扩展名）
        if video.url:
            base_names.append(os.path.splitext(video.url)[0])
        
        # 3. 使用视频名称（去掉扩展名）
        if video.name:
            base_names.append(os.path.splitext(video.name)[0])
        
        # 可能的字幕后缀
        suffixes = ['', '_zh', '_en', '_zh-CN', '_en-US']
        
        # 构建所有可能的文件路径
        possible_files = []
        for base_name in base_names:
            for suffix in suffixes:
                possible_files.append(os.path.join(srt_dir, f"{base_name}{suffix}.srt"))
        
        print(f"Looking for subtitle files: {possible_files}")
        
        for srt_path in possible_files:
            if os.path.exists(srt_path):
                print(f"Found subtitle file: {srt_path}")
                try:
                    with open(srt_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    print(f"读取字幕文件失败: {e}")
                    continue
        
        print(f"No subtitle files found in {srt_dir}")
        return ""
    
    def _get_video_path(self, video) -> str:
        """获取视频文件路径"""
        if video.url:
            video_dir = os.path.join(settings.MEDIA_ROOT, 'saved_video')
            video_path = os.path.join(video_dir, video.url)
            if os.path.exists(video_path):
                return video_path
        return ""
    
    def _get_frame_for_timestamp(
        self, 
        video_path: str, 
        timestamp: str, 
        output_dir: str,
        frame_cache: dict
    ) -> str:
        """获取指定时间戳的帧图片路径"""
        if timestamp in frame_cache:
            return frame_cache[timestamp]
        
        try:
            # 补全为 HH:MM:SS 格式
            if timestamp.count(':') == 1:
                timestamp = '00:' + timestamp
            
            secs = timestamp_to_seconds(timestamp)
            path = extract_frame(
                video_path=video_path,
                timestamp_seconds=secs,
                output_dir=output_dir
            )
            frame_cache[timestamp] = path
            return path
        except Exception as e:
            print(f"提取帧失败 {timestamp}: {e}")
            frame_cache[timestamp] = ""
            return ""
    
    def _process_content_timestamps(
        self, 
        content: str, 
        video_path: str,
        output_dir: str,
        frame_cache: dict
    ) -> str:
        """处理content中的时间戳标记，替换为图片Markdown"""
        # 匹配 [HH:MM:SS] 或 [MM:SS] 格式的时间戳
        pattern = r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]'
        
        def replace_timestamp(match):
            ts = match.group(1)
            # 补全为 HH:MM:SS 格式
            if ts.count(':') == 1:
                ts = '00:' + ts
            
            img_path = self._get_frame_for_timestamp(
                video_path, ts, output_dir, frame_cache
            )
            
            if img_path and os.path.exists(img_path):
                relative_path = os.path.relpath(img_path, settings.MEDIA_ROOT)
                img_url = f"/media/{relative_path.replace(os.sep, '/')}"
                return f'\n\n![{ts}]({img_url})\n\n'
            else:
                return match.group(0)
        
        return re.sub(pattern, replace_timestamp, content)


@method_decorator(csrf_exempt, name='dispatch')
class NoteFrameExtractView(View):
    """
    单帧提取API - 用于前端实时预览
    POST /api/notes/extract_frame/<video_id>
    """
    
    def post(self, request, video_id):
        """提取指定时间戳的帧"""
        try:
            # 获取视频
            try:
                video = Video.objects.get(pk=video_id)
            except Video.DoesNotExist:
                return JsonResponse({'success': False, 'error': '视频不存在'}, status=404)
            
            # 解析请求
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                data = {}
            
            timestamp = data.get('timestamp')
            if not timestamp:
                return JsonResponse({'success': False, 'error': '缺少时间戳参数'}, status=400)
            
            # 获取视频路径
            video_path = self._get_video_path(video)
            if not video_path:
                return JsonResponse({'success': False, 'error': '未找到视频文件'}, status=400)
            
            # 创建输出目录
            output_dir = os.path.join(
                settings.MEDIA_ROOT,
                'note_frames',
                f'video_{video_id}'
            )
            os.makedirs(output_dir, exist_ok=True)
            
            # 提取帧
            seconds = timestamp_to_seconds(timestamp)
            frame_path = extract_frame(
                video_path=video_path,
                timestamp_seconds=seconds,
                output_dir=output_dir
            )
            
            # 返回相对URL
            relative_path = os.path.relpath(frame_path, settings.MEDIA_ROOT)
            frame_url = f"/media/{relative_path.replace(os.sep, '/')}"
            
            return JsonResponse({
                'success': True,
                'data': {
                    'url': frame_url,
                    'timestamp': timestamp,
                    'seconds': seconds
                }
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    def _get_video_path(self, video) -> str:
        """获取视频文件路径"""
        if video.url:
            video_dir = os.path.join(settings.MEDIA_ROOT, 'saved_video')
            video_path = os.path.join(video_dir, video.url)
            if os.path.exists(video_path):
                return video_path
        return ""
