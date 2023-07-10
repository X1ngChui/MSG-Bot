import json
from concurrent.futures import Future, ThreadPoolExecutor
from queue import Queue

import requests

from group import Group
from instruction import Instruction
from message import Message


class Bot:
    _instance = None

    @classmethod
    def get_instance(cls) -> "Bot":
        if cls._instance is None:
            cls._instance = Bot()
        return cls._instance

    def __init__(self):
        self.running = True
        self.message_queue: Queue[Message] = Queue()
        self.groups: dict[int, Group] = dict()
        self.address = "http://127.0.0.1:5700"
        self.thread_pool = ThreadPoolExecutor()

    def add_message(self, message: Message) -> None:
        self.message_queue.put(message)

        if int(message.group_id) not in self.groups:
            self.groups[int(message.group_id)] = Group(int(message.group_id))

        reply = self.groups[int(message.group_id)].add_message(message)

        if reply is not None:
            self.thread_pool.submit(self.send_message, message)

    def send_message(self, message: Message) -> bool:
        url = self.address + "/send_group_msg"
        params = {
            "group_id": message.group_id,
            "message": json.dumps(message.message)
        }
        response = requests.post(url=url, params=params).json()
        if message.get_attached() is not None:
            try:
                message.get_attached().message_id = response["data"]["message_id"]
            except (TypeError, KeyError):
                message.message[1:] = [{"type": "text", "data": {"text": "Message delivery failed"}}]
                self.send_message(message)
                return False
        return response["status"] != "failed"

    def instruction_callback(self, future: Future) -> None:
        message = future.result()
        if message is not None:
            self.send_message(message)

    def run(self) -> None:
        while self.running:
            message = self.message_queue.get()
            instruction = Instruction.parse_instruction(message)
            future = self.thread_pool.submit(instruction.execute)
            future.add_done_callback(self.instruction_callback)

    def stop(self) -> None:
        self.running = False
