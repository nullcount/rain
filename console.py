"""
console.py
---
Use the current console (command line) as an AdminNotifyService
usage: for testing AdminNotifyService
"""
from config import config
from const import LOG_NOTIFY, LOG_INPUT
from base import AdminNotifyService
from result import Result, Ok, Err
from typing import Callable

class Console(AdminNotifyService):
    """
    Use the terminal/command line to notify events
        or seek approval for actions
    """
    def send_message(self, message: str) -> None:
        config.log(LOG_NOTIFY, message)
    
    def await_confirm(self, prompt: str, callback: Callable) -> Result[None, str]: # type: ignore
        config.log(LOG_INPUT, f"getting user input...")
        confirm = input(f"{prompt}: ")
        if confirm.capitalize() not in ['Y', 'YES']:
            config.log(LOG_INPUT, "input results in canceled action")
            return Err('Action was not confirmed.')
        config.log(LOG_INPUT, "input confirmed!")
        callback()
        return Ok(None)

    
