from fastapi import FastAPI
from dotenv import load_dotenv
from routers import auth, users, organizations, relief, foundations, volunteers, inkind, monetary

load_dotenv()

# cache_opts = {
#     'cache.type': 'file',
#     'cache.data_dir' : '/tmp/cache/data',
#     'cache.lock_dir': '/tmp/cache/lock'
# }

api_app = FastAPI(title="info api")
api_app.include_router(auth.router)
api_app.include_router(users.router)
api_app.include_router(organizations.router)
api_app.include_router(volunteers.router)
api_app.include_router(relief.router)
api_app.include_router(foundations.router)
api_app.include_router(inkind.router)
api_app.include_router(monetary.router)

app = FastAPI(title="main app")
app.mount("/api", api_app)