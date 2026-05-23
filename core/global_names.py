class GlobalNames:
    def __init__(self):
        self.title = "название"
        self.description = "описание"
        self.type = "тип"
        self.help_text = (
            f"❓Что умеет данный бот:\n\n"
            f"/help - Вызвать данное меню-помощник\n"
            f"/bin - Показать все удалённые элементы\n"
            f"• Списки\n"
            f"/new_list - Создать новый список\n"
        )  # f'/lists_view - Показать все списки\n'\
        # f'• Напоминания\n'\
        # f'/new_remind - Создать новое напоминание\n'\
        # f'/reminds_view - Просмотреть все напоминания'\

        self.list_view = {"type": "list", "action": "view"}
        self.values_view = {"type": "list", "action": "view", "inner": "values"}

    def get(self, name: str):
        return getattr(self, name)


GN = GlobalNames()
