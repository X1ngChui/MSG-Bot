from message import Message
from collections import deque


class Group:
    def __init__(self, group_id: int | str):
        self.group_id = group_id
        self.message_buffer: deque[Message] = deque(maxlen=128)

    def add_message(self, message: Message) -> Message | None:
        if str(message).startswith("/"):
            return None
        add, reply = self.check_repeat(message)
        if add:
            self.message_buffer.append(message)
        return reply

    def check_repeat(self, message: Message) -> tuple[bool, Message | None]:
        if len(self.message_buffer) and message == self.message_buffer[-1]:
            if not self.message_buffer[-1].repeated:
                self.message_buffer[-1].repeated = True
                return False, Message(group_id=message.group_id,
                                      message=message.message)
            else:
                return False, None
        else:
            return True, None

