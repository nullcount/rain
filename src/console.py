"""
console.py
---
Use stdout a.k.a. print() to log and read input from user
usage: anywhere
"""
from const import LOG_NOTIFY, LOG_INPUT
from result import Result, Ok, Err
from typing import Callable
from datetime import datetime

class console:
    """
    Use the terminal/command line to notify events
        or seek approval for actions
    """
    @staticmethod
    def log(level: str, message: str ) -> None:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {level.upper()}: {message}")
    
    def send_message(self, message: str) -> None:
        self.log(LOG_NOTIFY, message)
    
    def await_confirm(self, prompt: str, callback: Callable) -> Result[None, str]: # type: ignore
        self.log(LOG_INPUT, f"getting user input...")
        confirm = input(f"{prompt}: ")
        if confirm.capitalize() not in ['Y', 'YES']:
            self.log(LOG_INPUT, "input results in canceled action")
            return Err('Action was not confirmed.')
        self.log(LOG_INPUT, "input confirmed!")
        callback()
        return Ok(None)

    
