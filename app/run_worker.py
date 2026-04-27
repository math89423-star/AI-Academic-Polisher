"""
RQ Worker 启动脚本
"""
import os
from redis import Redis
from rq import Worker

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
redis_conn = Redis.from_url(redis_url)


def recover_orphaned_tasks():
    """启动时将卡在 processing 状态的孤儿任务标记为 failed"""
    from backend import create_app
    from backend.extensions import db
    from backend.model.models import Task

    app = create_app()
    with app.app_context():
        orphaned = Task.query.filter(Task.status == 'processing').all()
        if orphaned:
            for task in orphaned:
                task.status = 'failed'
            db.session.commit()
            print(f"[Worker启动恢复] 已将 {len(orphaned)} 个卡死任务标记为 failed")


if __name__ == '__main__':
    recover_orphaned_tasks()
    worker = Worker(['ai_tasks'], connection=redis_conn)
    worker.work()
