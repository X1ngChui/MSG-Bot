from typing import Callable
from message import Message
from pixiv_downloader import pixiv_downloader


class Syntax:
    def __init__(self, syntax: str | None, multiple: bool = False, final: bool = False,
                 function: Callable[[list, dict], Message] = None, reply: bool = False):
        # The syntax of the final syntax must be None
        assert syntax is not None or final
        # Syntax with multiple words must be the final syntax
        assert not multiple or final
        # The final syntax must be with a callback function
        assert not final == (function is None)

        self.syntax = syntax
        self.children = dict()
        self.multiple = multiple
        self.final = final
        self.function = function
        self.reply = reply

    def add_child(self, child: "Syntax") -> None:
        self.children[child.syntax] = child

    def __hash__(self):
        return hash(self.syntax)

    def __eq__(self, other):
        return self.syntax == other


class Instruction:
    # Create Syntax Tree
    _syntax_tree = Syntax("root")

    # /pixiv
    _pixiv = Syntax("/pixiv")
    _syntax_tree.add_child(_pixiv)

    # /pixiv tag
    _pixiv_tag = Syntax("tag")
    _pixiv_tag_parameter = Syntax(None, multiple=True, final=True, function=pixiv_downloader.get_illust_by_tags_impl)
    _pixiv.add_child(_pixiv_tag)
    _pixiv_tag.add_child(_pixiv_tag_parameter)

    # /pixiv illust id
    _pixiv_id = Syntax("id")
    _pixiv_id_parameter = Syntax(None, final=True, function=pixiv_downloader.get_illust_by_id_impl)
    _pixiv.add_child(_pixiv_id)
    _pixiv_id.add_child(_pixiv_id_parameter)

    # /pixiv info
    _pixiv_info = Syntax("info", final=True, reply=True, function=pixiv_downloader.get_illust_info_impl)
    _pixiv.add_child(_pixiv_info)

    # /pixiv origin
    _pixiv_origin = Syntax("origin", final=True, reply=True, function=pixiv_downloader.get_origin_illust_impl)
    _pixiv.add_child(_pixiv_origin)

    def __init__(self):
        self.valid = True
        self.function = None
        self.args = list()
        self.kwargs = dict()

    def execute(self) -> Message | None:
        if self.valid:
            return self.function(self.args, self.kwargs)
        else:
            return None

    @classmethod
    def parse_instruction(cls, message: Message) -> "Instruction":
        instruction = Instruction()
        instruction_syntax = str(message).strip().split()
        reply = False

        # ----- reserved arguments -----
        instruction.kwargs["group_id"] = message.group_id
        instruction.kwargs["message_id"] = message.message_id
        instruction.kwargs["user_id"] = message.user_id

        for element in message.message:
            if element["type"] == "reply":
                instruction.kwargs["earlier_text"] = int(element["data"]["id"])
                reply = True
                break
        # ------------------------------

        now = cls._syntax_tree
        index = 0

        while instruction.valid and index < len(instruction_syntax):
            for child in now.children.values():
                if child.syntax == instruction_syntax[index] or child.syntax is None:
                    if child.multiple:
                        index += 1
                        while index < len(instruction_syntax) and not instruction_syntax[index].startswith("-"):
                            if not instruction_syntax[index - 1].startswith("-"):
                                instruction.args.append(instruction_syntax[index - 1])
                            else:
                                instruction.valid = False
                            index += 1
                        instruction.args.append(instruction_syntax[index - 1])
                    if child.final:
                        instruction.valid &= child.reply == reply
                        if not child.multiple:
                            instruction.args.append(instruction_syntax[index])
                            index += 1
                        instruction.function = child.function
                        while instruction.valid and index < len(instruction_syntax):
                            if not instruction_syntax[index].startswith("-"):
                                instruction.valid = False
                            elif index < len(instruction_syntax) - 1 and not instruction_syntax[index + 1].startswith(
                                    "-"):
                                instruction.kwargs[instruction_syntax[index]] = instruction_syntax[index + 1]
                                index += 2
                            else:
                                instruction.kwargs[instruction_syntax[index]] = True
                                index += 1
                    now = child
                    break
            else:
                instruction.valid = False
            index += 1

        instruction.valid &= instruction.function is not None
        return instruction

