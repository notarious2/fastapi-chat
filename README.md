
# NOTICE
# I could no longer maintain custom domain, please use
https://vuetify-chat.vercel.app/
# to see the demo



# Real-time Chat App with FastAPI

Live Demo: https://vuetify-chat.vercel.app/

Swagger UI: https://fastapi-chat-2bfa6dd112d2.herokuapp.com/docs

Admin: https://fastapi-chat-2bfa6dd112d2.herokuapp.com/admin/ (login: `bekzod`, password: `bekzod`)

#### Frontend with Vue 3 and Vuetify 3, see <a href="https://github.com/notarious2/vuetify-chat">repo</a> 

### Tech Stack:
- FastAPI, Websockets, Pydantic 2
- Postgres (asyncpg), async Redis (PubSub and Cache)
- SQLAlchemy 2
- Database migrations with Alembic
- Poetry for dependency management, containerization with Docker/docker-compose
- Linting and Formatting with <strong>Ruff</strong>

### High level functionality description
- Fully asynchronous: FastAPI, Postgres, Redis
- JWT HTTP-only cookies authentication (access, refresh tokens)
- Horizontal Scalability with Redis PubSub
- Rate Limiting (Throttling)
- FastAPI background tasks: 
  - uploading photos to cloud 
  - updating non-essential info
- Message status confirmation: sending, sent and read
- Read status tracking with one field per user per chat (last read message) instead of tracking  individual message read status
- User status tracking: online, inactive and offline
- User `is typing` tracking
- Google Oauth2 authentication:
  - Frontend retrieves access token
  - Backend verifies and gets user data
- Store files in AWS S3 bucket in production and StaticFiles in local development
- Modern Admin panel with `sqladmin`

### Local Setup
- Configure necessary variables in `src/config.py`
- Create network: `make network`
- Build and run: `make build-up` (runs on port: 8001)
- Apply migrations: `make upgrade`
- Follow logs: `make logs`
- Run tests: `make test`
  
<img width="864" alt="Screenshot 2024-02-18 at 18 37 11" src="https://github.com/notarious2/fastapi-chat/assets/104051317/27df9a18-5131-4e39-a80e-103f8b9ba5e8">
