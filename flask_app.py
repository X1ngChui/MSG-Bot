from flask import Flask, request
from bot import Bot
from message import Message

app = Flask(__name__)


@app.route("/", methods=["POST"])
def post_msg() -> str:
    msg = request.get_json()
    if msg["post_type"] == "message" and msg["message_type"] == "group":
        Bot.get_instance().add_message(Message(group_id=msg["group_id"],
                                               message=msg["message"],
                                               message_id=msg["message_id"],
                                               user_id=msg["user_id"]))
    return "OK"
