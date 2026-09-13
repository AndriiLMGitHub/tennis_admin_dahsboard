from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class MailEvent:
    subject: str
    body: str
    recipients: List[str]

    html: Optional[str] = None
    context: Optional[Dict] = None