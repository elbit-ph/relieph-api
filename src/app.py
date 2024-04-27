from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import auth, users, organizations, relief, foundations, volunteers, inkind, monetary, headlines, reports
from util.scheduler.schedule import sched

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
api_app.include_router(reports.router)

app = FastAPI(title="main app")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"], # Allows all origins
	allow_credentials=True,
	allow_methods=["*"], # Allows all methods
	allow_headers=["*"] # Allows all headers
)

app.mount("/api", api_app)

sched.start()