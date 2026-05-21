from pydantic import BaseModel


class GlobalNames(BaseModel):
    title: str = "название"
    description: str = "описание"
    type: str = "тип"

    def get(self, name: str):
        return getattr(self, name)


GN = GlobalNames()
