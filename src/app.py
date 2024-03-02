from fastapi import Depends, FastAPI, Response
from dotenv import load_dotenv
from routers import test
from dependencies import get_logger

load_dotenv()

cache_opts = {
    'cache.type': 'file',
    'cache.data_dir' : '/tmp/cache/data',
    'cache.lock_dir': '/tmp/cache/lock'
}

api_app = FastAPI(title="info api")
api_app.include_router(test.router)

app = FastAPI(title="main app")
app.mount("/api", api_app)