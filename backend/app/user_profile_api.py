"""Authenticated users manage their own contact information, never account roles."""
import re
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import Field, StringConstraints, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models as m
from app.api import current, db, save
from app.schemas import Input

ContactText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class ContactProfile(Input):
    phone: Annotated[str, StringConstraints(max_length=40)] | None = None
    email: Annotated[str, StringConstraints(max_length=254)] | None = None
    division: ContactText | None = None
    work_area: ContactText | None = None

    @field_validator('phone', 'email', 'division', 'work_area', mode='before')
    @classmethod
    def trim(cls, value):
        return (value.strip() or None) if isinstance(value, str) else value

    @field_validator('phone')
    @classmethod
    def phone_number(cls, value):
        if value is None:
            return None
        value = re.sub(r'[ ()-]', '', value)
        if not re.fullmatch(r'\+?[0-9]{8,16}', value):
            raise ValueError('Isi nomor WA 8–16 digit, boleh diawali +')
        return value

    @field_validator('email')
    @classmethod
    def email_address(cls, value):
        if value is not None and not re.fullmatch(r'[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+', value):
            raise ValueError('Isi alamat email kantor yang valid')
        return value


class ProfileUpdate(ContactProfile):
    expected_version: int = Field(ge=0)


class ProfileOutput(ContactProfile):
    version: int = Field(ge=0)


def profile_info(user):
    stored = user.contact_profile or {}
    return {key: stored.get(key) for key in ContactProfile.model_fields} | {'version': stored.get('version', 0)}


router = APIRouter(prefix='/auth/me/profile', tags=['My profile'])


@router.get('', response_model=ProfileOutput)
def read_profile(response: Response, user=Depends(current)):
    response.headers['Cache-Control'] = 'private, no-store'
    return profile_info(user)


@router.put('', response_model=ProfileOutput)
def update_profile(data: ProfileUpdate, response: Response, user=Depends(current), session: Session = Depends(db)):
    locked = session.scalar(select(m.User).where(m.User.id == user.id).with_for_update().execution_options(populate_existing=True))
    existing = locked.contact_profile or {}
    if data.expected_version != existing.get('version', 0):
        raise HTTPException(409, 'Profil server berubah. Draf tetap disimpan; muat profil terbaru untuk meninjau perubahan.')
    locked.contact_profile = {**existing, **data.model_dump(exclude={'expected_version'}), 'version': data.expected_version + 1}
    save(session)
    response.headers['Cache-Control'] = 'private, no-store'
    return profile_info(locked)
