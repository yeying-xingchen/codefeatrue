from typing import Union
from fastapi import FastAPI

app = FastAPI()

@app.post("/")
def main(info: dict):
    if info["post_type"]=="message":
        if info["message_type"] == "private":
                return {
                    "reply": "嗨～"+info["sender"]["nickname"]
                }
        if info["message_type"] == "group":
                if info["sender"]["nickname"] == "夜影星辰":
                    print(info["raw_message"])
                    return {
                        "reply": info["raw_message"]
                    }
    return {
        "message": "Item created"
    }