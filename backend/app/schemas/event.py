from typing import Literal
from pydantic import BaseModel

# -- INPUT MODEL

class EventCreate(BaseModel):
    customer_id = str
    event_id = bool
    event_type = str