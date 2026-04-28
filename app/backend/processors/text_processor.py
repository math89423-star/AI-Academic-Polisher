"""
文本任务处理器

负责处理纯文本润色任务
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.processors.base_processor import BaseTaskProcessor
from backend.utils.helpers import split_text_into_chunks
from backend.config import WorkerConfig, RedisKeyManager
from backend.extensions import db
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


class TextTaskProcessor(BaseTaskProcessor):
    """文本任务处理器"""

    def process(self) -> None:
        """处理文本任务"""
        # 切片文本
        chunks = split_text_into_chunks(
            self.task.original_text,
            max_chars=WorkerConfig.get_chunk_size()
        )
        total_chunks = len(chunks)

        logger.info(f"任务 {self.task_id} 切分为 {total_chunks} 个片段")

        if total_chunks <= 1:
            # 短文本：流式输出
            self._process_short_text()
        else:
            # 长文本：并发处理
            self._process_long_text(chunks, total_chunks)

    def _process_short_text(self) -> None:
        """处理短文本（流式输出）"""
        logger.info(f"任务 {self.task_id} 使用流式处理")

        self.progress_publisher.publish_block("🚀 AI 正在实时生成润色内容...\n\n")

        full_text = self.task.polished_text or ""
        generator = self.ai_service.generate_stream(
            text=self.task.original_text,
            mode=self.task.mode,
            strategy=self.task.strategy,
            history_text=self.task.polished_text
        )

        inside_think = False
        buf = ""

        for chunk in generator:
            if self.check_cancellation():
                self.task.polished_text = full_text
                db.session.commit()
                return

            buf += chunk

            while buf:
                if inside_think:
                    end_pos = buf.lower().find("</think>")
                    if end_pos != -1:
                        buf = buf[end_pos + 8:]
                        inside_think = False
                    else:
                        buf = buf[-8:] if len(buf) > 8 else buf
                        break
                else:
                    start_pos = buf.lower().find("<think>")
                    if start_pos != -1:
                        clean = buf[:start_pos]
                        if clean:
                            full_text += clean
                            self.progress_publisher.publish_stream(clean)
                        buf = buf[start_pos + 7:]
                        inside_think = True
                    else:
                        safe = buf[:-7] if len(buf) > 7 else ""
                        if safe:
                            full_text += safe
                            self.progress_publisher.publish_stream(safe)
                        buf = buf[len(safe):]
                        break

        if buf and not inside_think:
            full_text += buf
            self.progress_publisher.publish_stream(buf)

        self.task.polished_text = full_text
        db.session.commit()

    def _process_long_text(self, chunks: list[str], total_chunks: int) -> None:
        """处理长文本（并发处理）"""
        logger.info(f"任务 {self.task_id} 使用并发处理 ({WorkerConfig.MAX_WORKERS} 线程)")

        progress_key = RedisKeyManager.progress_key(self.task_id)

        # 从Redis恢复已完成的片段
        raw_done = self.redis_client.hgetall(progress_key)
        done_dict = {int(k): v for k, v in raw_done.items()} if raw_done else {}

        # 找出未完成的片段
        chunks_to_process = [
            (i, txt) for i, txt in enumerate(chunks) if i not in done_dict
        ]

        if chunks_to_process:
            self.progress_publisher.publish_block(
                f"📝 长文本切片成功！共 {total_chunks} 个片段。\n"
                f"🚀 【多线程并发】引擎已激活，正在处理...\n\n"
            )

            completed_count = len(done_dict)

            with ThreadPoolExecutor(max_workers=WorkerConfig.MAX_WORKERS) as executor:
                # 提交所有任务
                future_to_chunk = {
                    executor.submit(self._process_single_chunk, idx, text): (idx, text)
                    for idx, text in chunks_to_process
                }

                # 处理完成的任务
                for future in as_completed(future_to_chunk):
                    # 检查取消信号
                    if self.check_cancellation():
                        return

                    idx, original_chunk = future_to_chunk[future]

                    try:
                        polished_chunk = future.result()

                        # 如果返回结果太短，使用原文
                        if not polished_chunk or len(polished_chunk.strip()) < 5:
                            polished_chunk = original_chunk

                        done_dict[idx] = polished_chunk
                        self.redis_client.hset(progress_key, str(idx), polished_chunk)

                        completed_count += 1

                        # 推送进度
                        progress = int((completed_count / total_chunks) * 100)
                        self.progress_publisher.publish_progress(progress)
                        self.progress_publisher.publish_block(
                            f"⚡ [并发加速] 第 {completed_count}/{total_chunks} 个片段完成...\n"
                        )

                    except Exception as e:
                        logger.error(f"处理片段 {idx} 失败: {str(e)}")
                        # 失败时使用原文
                        done_dict[idx] = original_chunk
                        completed_count += 1

        # 合并所有片段
        final_text_parts = [done_dict.get(i, chunks[i]) for i in range(total_chunks)]
        final_text = "\n\n".join(final_text_parts)

        self.task.polished_text = final_text
        db.session.commit()

        # 推送最终结果（完整替换，非增量追加）
        self.progress_publisher.publish_full(final_text)

        # 清理Redis缓存
        self.redis_client.delete(progress_key)

    def _process_single_chunk(self, chunk_idx: int, text_content: str) -> str:
        """
        处理单个文本片段

        Args:
            chunk_idx: 片段索引
            text_content: 文本内容

        Returns:
            str: 润色后的文本
        """
        logger.debug(f"处理片段 {chunk_idx}")

        return self.ai_service.generate_sync(
            text=text_content,
            mode=self.task.mode,
            strategy=self.task.strategy
        )

    def handle_failure(self, exception: Exception) -> None:
        """处理失败情况"""
        # 保存已完成的部分
        if hasattr(self, 'full_text') and self.full_text:
            self.task.polished_text = self.full_text
            db.session.commit()
            logger.info(f"任务 {self.task_id} 失败，已保存部分结果")

    def cleanup(self) -> None:
        """清理资源"""
        super().cleanup()
        # 清理进度缓存
        progress_key = RedisKeyManager.progress_key(self.task_id)
        self.redis_client.delete(progress_key)
