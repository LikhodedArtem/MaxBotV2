from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).parent.parent

DB_PATH = BASE_DIR / "db.sqlite3"


class DbSettings(BaseModel):
    url: str = f"sqlite+aiosqlite:///{DB_PATH}"
    echo: bool = False


class Settings(BaseSettings):
    api_prefix: str = "/api/v2"

    db: DbSettings = DbSettings()


settings = Settings()


class BotInfo(BaseModel):
    token: str = (
        "f9LHodD0cOK2Vf61z0Rirqtgyg6o29wjLbwM-RVkdGC8lZ4W26uYQuCTXS5mt7FzMrBVqjVVavmgJIB26Ofe"
    )
    free_lists_max_count: int = 5
    my_id: int = 257767688


bot_info = BotInfo()


class RequestSettings:
    url = "https://platform-api.max.ru"
    headers = {"Authorization": bot_info.token, "Content-Type": "application/json"}


request_settings = RequestSettings()