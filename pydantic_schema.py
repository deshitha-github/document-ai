from pydantic import BaseModel
from pydantic import Field
# from typing import List, Optional, Literal, Dict, Any


# Define Pydantic schema for order
class GetOrderId(BaseModel):
    order_id: int = Field(..., description="The order ID for the product")