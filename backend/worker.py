"""
RQ Worker script for Skill Synth AI.
"""
import sys
import os
sys.path.insert(0, os.getcwd())
from redis import Redis
from rq import SimpleWorker, Queue
from backend import create_app

# Set up the app context for the worker
app = create_app()

def start_worker():
    redis_url = app.config.get("REDIS_URL", "redis://localhost:6379/0")
    redis_conn = Redis.from_url(redis_url)
    
    q = Queue("default", connection=redis_conn)
    # Use SimpleWorker on Windows because os.fork() is not available
    worker = SimpleWorker([q], connection=redis_conn)
    worker.work()

if __name__ == "__main__":
    start_worker()
