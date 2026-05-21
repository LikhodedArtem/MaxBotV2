from pydantic import BaseModel

from typing import Optional


class Update(BaseModel):
    timestamp: int
    user_locale: str
    update_type: Optional[str]
