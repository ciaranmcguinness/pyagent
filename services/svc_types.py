from dataclasses import dataclass
from typing import Callable, Literal, Any


@dataclass
class Service():
    fn: Callable[[Any],None]
    trigger: Literal["on_start","on_exit","on_message"]