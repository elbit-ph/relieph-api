from fastapi import FastAPI
from dotenv import load_dotenv
from routers import auth, users, organizations, relief, foundations, volunteers, inkind, monetary, headlines
from util.headline_classifier.scheduler import scheduler

load_dotenv()

# cache_opts = {
#     'cache.type': 'file',
#     'cache.data_dir' : '/tmp/cache/data',
#     'cache.lock_dir': '/tmp/cache/lock'
# }

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     startup_event(background_tasks, db)
#     yield

api_app = FastAPI(title="info api")
api_app.include_router(auth.router)
api_app.include_router(users.router)
api_app.include_router(organizations.router)
api_app.include_router(volunteers.router)
api_app.include_router(relief.router)
api_app.include_router(foundations.router)
api_app.include_router(inkind.router)
api_app.include_router(monetary.router)
api_app.include_router(headlines.router)

app = FastAPI(title="main app")
app.mount("/api", api_app)

scheduler.start()
