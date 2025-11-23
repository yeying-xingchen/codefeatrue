from typing import Union
from fastapi import FastAPI
from plugins import github

app = FastAPI()

@app.post("/")
def main(info: dict):
    if info["post_type"]=="message":
        if info["message_type"] == "group":
            if info["raw_message"].startswith("/github"):
                return github.on_command(info)
    return {}