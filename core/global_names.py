from pydantic import BaseModel


class GlobalNames(BaseModel):
    title: str = "название"
    description: str = "описание"
    type: str = "тип"
    help_text: str = (
        f"❓Что умеет данный бот:\n\n"
        f"/help - Вызвать данное меню-помощник\n"
        f"/reg - Регистрация в боте\n"
        f"/bin - Показать все удалённые элементы\n"
        f"• Списки\n"
        f"/new_list - Создать новый список\n"
    )  # f'/lists_view - Показать все списки\n'\
    # f'• Напоминания\n'\
    # f'/new_remind - Создать новое напоминание\n'\
    # f'/reminds_view - Просмотреть все напоминания'\

    def get(self, name: str):
        return getattr(self, name)


GN = GlobalNames()
