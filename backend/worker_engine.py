# backend/worker_engine.py
import json
import os
import docx
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.extensions import db, redis_client
from backend import create_app
from backend.model import Task, User, ApiConfig
from backend.utils.ai_service import pure_ai_generator, sync_ai_request, remove_thinking_tags
from backend.utils.docx_service import is_paragraph_needs_polishing, replace_paragraph_text, check_stop_signal
from backend.utils.helpers import split_text_into_chunks # 🟢 引入你之前写好的智能切片工具

app = create_app()

def process_task(task_id):
    with app.app_context():
        task = Task.query.get(task_id)
        if not task: return
        user = User.query.get(task.user_id)
        channel_name = f"stream:task:{task_id}"
        
        print(f"\n=======================================")
        print(f"🚀 [Worker] 开始处理任务 ID: {task_id}")
        print(f"📂 [Worker] 数据库记录的任务类型: {task.task_type}")
        print(f"=======================================\n")
        
        api_key, base_url, model_name = None, None, 'gpt-3.5-turbo'
        if user and user.api_config:
            api_key, base_url, model_name = user.api_config.api_key, user.api_config.base_url, user.api_config.model_name
        else:
            default_config = ApiConfig.query.first()
            if default_config:
                api_key, base_url, model_name = default_config.api_key, default_config.base_url, default_config.model_name
        
        if not api_key or not base_url:
            _publish_error(channel_name, "系统未配置可用的 API 线路。")
            task.status = 'failed'
            db.session.commit()
            return

        task.status = 'processing'
        db.session.commit()
        
        full_text = ""
        doc = None

        try:
            # ==========================================
            # 分支 1：处理纯文本任务 (融合流式与并发引擎)
            # ==========================================
            if task.task_type == 'text' or not getattr(task, 'task_type', None):
                print("📝 [Worker] 判定结果：进入【纯文本】处理分支")
                
                # 1. 智能切片
                chunks = split_text_into_chunks(task.original_text, max_chars=600)
                total_chunks = len(chunks)
                
                if total_chunks <= 1:
                    # 2A. 如果是很短的文本，保持流式打字机的丝滑视觉体验
                    _publish_message(channel_name, "block", "AI 正在接管任务，请稍候...\n\n")
                    full_text = task.polished_text or ""
                    generator = pure_ai_generator(
                        text=task.original_text, api_key=api_key, base_url=base_url,
                        model_name=model_name, mode=task.mode, history_text=task.polished_text
                    )
                    for chunk in generator:
                        cancel_key = f"cancel:task:{task_id}"
                        if redis_client.exists(cancel_key):
                            task.status = 'cancelled'
                            task.polished_text = remove_thinking_tags(full_text)
                            db.session.commit()
                            redis_client.delete(cancel_key)
                            print("⏹ [Worker] 短文本任务已手动终止")
                            return
                        full_text += chunk
                        _publish_message(channel_name, "stream", chunk)
                    
                    task.polished_text = remove_thinking_tags(full_text)
                
                else:
                    # 2B. 如果是长篇文本，立刻激活并发矩阵！
                    progress_key = f"text_progress:task:{task_id}"
                    
                    # 读取 Redis 里的 Hash 断点（哪怕任务被终止过，也能精准提取已经完成的片段）
                    raw_done = redis_client.hgetall(progress_key)
                    done_dict = {int(k): v for k, v in raw_done.items()} if raw_done else {}
                    
                    # 筛选出还没处理的片段
                    chunks_to_process = [(i, txt) for i, txt in enumerate(chunks) if i not in done_dict]
                    
                    if not chunks_to_process:
                        if done_dict:
                            _publish_message(channel_name, "block", "📝 断点恢复检查：所有文本片段均已处理完毕！\n\n")
                    else:
                        _publish_message(channel_name, "block", f"📝 长文本智能切片成功！共 {total_chunks} 个片段。\n🚀 【多线程并发引擎】已激活，正在极速为您润色...\n\n")
                        
                        def process_single_chunk(chunk_idx, text_content):
                            res = sync_ai_request(
                                text=text_content, api_key=api_key, base_url=base_url,
                                model_name=model_name, mode=task.mode
                            )
                            return chunk_idx, remove_thinking_tags(res)

                        completed_count = len(done_dict)
                        is_cancelled = False
                        
                        # 开启线程池爆破
                        MAX_CONCURRENCY = 15
                        with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as executor:
                            future_to_chunk = {executor.submit(process_single_chunk, p[0], p[1]): p for p in chunks_to_process}
                            
                            for future in as_completed(future_to_chunk):
                                # 时刻监听终止信号
                                cancel_key = f"cancel:task:{task_id}"
                                if redis_client.exists(cancel_key):
                                    is_cancelled = True
                                    task.status = 'cancelled'
                                    db.session.commit()
                                    redis_client.delete(cancel_key)
                                    break
                                
                                idx = future_to_chunk[future][0]
                                original_chunk = future_to_chunk[future][1]
                                
                                try:
                                    _, polished_chunk = future.result()
                                    if not polished_chunk or len(polished_chunk.strip()) < 5:
                                        print(f"⚠️ [Worker] 文本片段 {idx} 返回异常空值，已回滚原文保护。")
                                        polished_chunk = original_chunk

                                    done_dict[idx] = polished_chunk
                                    # 乱序写入：每完成一段，立刻安全锁入 Redis！
                                    redis_client.hset(progress_key, str(idx), polished_chunk)
                                    completed_count += 1
                                    
                                    # 向前端推送进度
                                    _publish_message(channel_name, "block", f"⚡ [并发加速] 第 {completed_count}/{total_chunks} 个文本片段已润色完成...\n")
                                except Exception as exc:
                                    print(f"❌ [Worker] 文本片段 {idx} 并发请求失败: {exc}")
                                    # 兜底机制：即使某段网络错误，保底使用原文，不影响其他片段
                                    done_dict[idx] = original_chunk 
                                    redis_client.hset(progress_key, str(idx), original_chunk)
                                    completed_count += 1
                        
                        if is_cancelled:
                            print(f"⏹ [Worker] 长文本并发任务被终止，进度已存在 Redis 中保护。")
                            return
                            
                    # 所有片段全军出击完成，进行无缝拼接
                    final_text_parts = [done_dict.get(i, chunks[i]) for i in range(total_chunks)]
                    final_text = "\n\n".join(final_text_parts) # 段落之间加入换行符
                    
                    task.polished_text = final_text
                    
                    # 瞬间将拼接好的全篇万字长文推送到前端直接显示！
                    _publish_message(channel_name, "stream", final_text)
                    
                    # 扫尾：清除完成的 Redis 进度缓存，避免日后再点重复加载
                    redis_client.delete(progress_key)

            # ==========================================
            # 分支 2：DOCX 文档任务
            # ==========================================
            elif task.task_type == 'docx':
                print("📄 [Worker] 判定结果：进入【Word文档-高并发】解析分支")
                
                done_indices_key = f"docx_done_indices:task:{task_id}"
                raw_done = redis_client.smembers(done_indices_key)
                done_indices = {int(x) for x in raw_done} if raw_done else set()
                
                file_to_load = task.result_file_path if (task.result_file_path and len(done_indices) > 0) else task.file_path
                print(f"📂 [Worker] 正在加载物理文档: {file_to_load}")
                
                doc = docx.Document(file_to_load)
                
                paras_to_process = []
                stop_processing = False
                for i, para in enumerate(doc.paragraphs):
                    if stop_processing: break
                    if check_stop_signal(para.text): 
                        print("🛑 [Worker] 检测到参考文献，停止解析后续正文。")
                        stop_processing = True
                        break
                    if i in done_indices: continue 
                        
                    if is_paragraph_needs_polishing(para):
                        paras_to_process.append((i, para.text))
                        
                total_paras = len(paras_to_process)
                
                if total_paras == 0:
                    if len(done_indices) > 0:
                        _publish_message(channel_name, "block", "📄 断点恢复检查：所有段落均已处理完毕！\n\n")
                    else:
                        _publish_message(channel_name, "block", "📄 文档解析完毕，未找到符合条件的中文正文段落。\n\n")
                else:
                    _publish_message(channel_name, "block", f"📄 解析成功！共提取 {total_paras} 个核心段落待处理。\n🚀 【多线程并发引擎】已激活，正在满载提速...\n\n")
                    
                    def process_single_para(para_idx, text_content):
                        # 终极防护：如果遇到长达千字不按回车的“毒瘤段落”，进行段内再切片
                        if len(text_content) > 600:
                            sub_chunks = split_text_into_chunks(text_content, max_chars=600)
                            polished_sub = []
                            for sc in sub_chunks:
                                res = sync_ai_request(
                                    text=sc, api_key=api_key, base_url=base_url,
                                    model_name=model_name, mode=task.mode
                                )
                                polished_sub.append(remove_thinking_tags(res))
                            return para_idx, "".join(polished_sub)
                        else:
                            # 正常段落直接发送
                            res = sync_ai_request(
                                text=text_content, api_key=api_key, base_url=base_url,
                                model_name=model_name, mode=task.mode
                            )
                            return para_idx, remove_thinking_tags(res)

                    results_dict = {}
                    completed_count = 0
                    is_cancelled = False
                    
                    MAX_CONCURRENCY = 15
                    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as executor:
                        future_to_para = {executor.submit(process_single_para, p[0], p[1]): p for p in paras_to_process}
                        
                        for future in as_completed(future_to_para):
                            cancel_key = f"cancel:task:{task_id}"
                            if redis_client.exists(cancel_key):
                                is_cancelled = True
                                task.status = 'cancelled'
                                redis_client.delete(cancel_key)
                                break 
                            
                            para_tuple = future_to_para[future]
                            idx = para_tuple[0]
                            original_text = para_tuple[1]
                            
                            try:
                                _, polished_text = future.result()
                                if not polished_text or len(polished_text.strip()) < 5:
                                    print(f"⚠️ [Worker] Word段落 {idx} 返回异常空值，已回滚原文保护。")
                                    polished_text = original_text
                                results_dict[idx] = polished_text
                                completed_count += 1
                                
                                redis_client.sadd(done_indices_key, idx)
                                _publish_message(channel_name, "block", f"⚡ [并发加速] 第 {completed_count}/{total_paras} 个段落已完成覆盖...\n")
                                
                            except Exception as exc:
                                print(f"❌ [Worker] 段落 {idx} 并发请求失败: {exc}")
                                results_dict[idx] = original_text 
                                
                    for idx, new_text in results_dict.items():
                        replace_paragraph_text(doc.paragraphs[idx], new_text)
                        
                    if is_cancelled:
                        temp_path = os.path.join('outputs', f"polished_temp_{task.id}.docx")
                        doc.save(temp_path)
                        task.result_file_path = temp_path
                        db.session.commit()
                        print(f"⏹ [Worker] 任务被终止，临时并发进度已存至: {temp_path}")
                        return
                
                output_path = os.path.join('outputs', f"polished_{task.id}.docx")
                doc.save(output_path)
                task.result_file_path = output_path
                
                redis_client.delete(done_indices_key) 
                redis_client.delete(f"docx_progress:task:{task_id}") 
                
                print(f"✅ [Worker] 文档已并发处理完毕并保存至: {output_path}")
                _publish_message(channel_name, "block", "\n\n🎉 全局高并发重排完毕，正在生成下载链接...\n")

            # ==========================================
            # 统一收尾操作
            # ==========================================
            task.status = 'completed'
            db.session.commit()
            if task.task_type == 'docx':
                _publish_message(channel_name, "download", f"/api/tasks/download/{task.id}")
            _publish_message(channel_name, "done", "完成")
            print("🎉 [Worker] 任务彻底完成并退出！")
            
        except Exception as e:
            print(f"❌ [Worker] 发生严重报错退出: {str(e)}")
            task.status = 'failed'
            if task.task_type == 'text':
                if 'full_text' in locals() and full_text: 
                    task.polished_text = remove_thinking_tags(full_text)
            elif task.task_type == 'docx' and doc is not None:
                temp_path = os.path.join('outputs', f"polished_temp_{task.id}.docx")
                doc.save(temp_path)
                task.result_file_path = temp_path
            db.session.commit()
            _publish_error(channel_name, f"发生网络或解析异常: {str(e)}")

def _publish_message(channel_name, msg_type, content):
    payload = json.dumps({"type": msg_type, "content": content})
    redis_client.publish(channel_name, f"data: {payload}\n\n")

def _publish_error(channel_name, error_msg):
    payload = json.dumps({"type": "fatal", "content": error_msg})
    redis_client.publish(channel_name, f"data: {payload}\n\n")