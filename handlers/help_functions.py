from core.models.mylist_value import MyListValue
from sqlalchemy.orm import Mapped

def mylist_values_to_form(
    mylist_values: list[MyListValue] | Mapped[list[MyListValue]],
):
    if len(mylist_values) == 0:
        values_text = f"    • Пока что нет\n"
    else:
        values_text = ""

        for i, value in enumerate(mylist_values):
            cod1, cod2 = "", ""
            # if value.made: не реализованно
            #     continue
            if value.made:
                cod1, cod2 = "<strike>", "</strike>"

            values_text += f"  /{i + 1}  {cod1} {value.value} {cod2}\n"
    return values_text