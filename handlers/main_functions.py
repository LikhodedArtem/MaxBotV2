from broker import broker
from broker.event import Event
from messages.message_schemes import Message

@broker.check(Event.MESSAGE_CREATED)
async def message_handler(message: Message) -> None:
    await message.answer(f"Вы написали: {message.body.text}")