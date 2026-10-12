from types import SimpleNamespace
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi import HTTPException

from app.core.dependencies import get_current_user

pytestmark = pytest.mark.asyncio


class TestCoreDependencies:
    async def test_get_current_user_missing_token_raises_401(self):
        db = SimpleNamespace()

        with pytest.raises(HTTPException) as exc:
            await get_current_user(access_token=None, db=db)
        assert exc.value.status_code == 401

    async def test_get_current_user_invalid_jwt_raises_401(self, monkeypatch):
        db = SimpleNamespace()
        monkeypatch.setattr(
            "app.core.dependencies.jwt.decode",
            lambda *args, **kwargs: (_ for _ in ()).throw(jwt.PyJWTError("bad")),
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(access_token="test-token", db=db)
        assert exc.value.status_code == 401

    async def test_get_current_user_payload_without_sub_raises_401(self, monkeypatch):
        db = SimpleNamespace()
        monkeypatch.setattr(
            "app.core.dependencies.jwt.decode",
            lambda *args, **kwargs: {},
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(access_token="test-token", db=db)
        assert exc.value.status_code == 401

    async def test_get_current_user_inactive_user_raises_401(self, monkeypatch):
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(
                    scalar_one_or_none=lambda: SimpleNamespace(username="alice", is_active=False)
                )
            )
        )

        monkeypatch.setattr(
            "app.core.dependencies.jwt.decode",
            lambda *args, **kwargs: {"sub": "alice"},
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(access_token="test-token", db=db)
        assert exc.value.status_code == 401

    async def test_get_current_user_valid_token_returns_user(self, monkeypatch):
        expected_user = SimpleNamespace(username="alice", is_active=True)

        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(scalar_one_or_none=lambda: expected_user)
            )
        )
        monkeypatch.setattr(
            "app.core.dependencies.jwt.decode",
            lambda *args, **kwargs: {"sub": "alice"},
        )

        user = await get_current_user(access_token="test-token", db=db)

        assert user == expected_user
