from typing import Any


class Message:
    def __init__(self, message: list[dict], group_id: int | str = None,
                 message_id: int | str | None = None, user_id: int | str | None = None,
                 attached: Any = None):
        self.message_id = message_id
        self.user_id = user_id
        self.group_id = group_id
        self.message = message
        self.repeated = False
        self.attached = attached

    def set_attached(self, attached) -> None:
        assert hasattr(attached, "message_id")
        self.attached = attached

    def get_attached(self) -> Any:
        return self.attached

    def __str__(self):
        text = [element["data"]["text"] for element in self.message if element.get("type", None) == "text"]
        return " ".join(text)

    def __eq__(self, other):
        if isinstance(other, Message):
            return self.message == other.message
        else:
            return False
