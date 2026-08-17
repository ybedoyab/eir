from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class ContactChannel(StrEnum):
    VOICE = "voice"
    SMS = "sms"
    EMAIL = "email"


class Patient(BaseModel):
    id: str
    name: str
    date_of_birth: date
    preferred_language: str = "en"
    preferred_contact_channel: ContactChannel = ContactChannel.VOICE
