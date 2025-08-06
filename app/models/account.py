import enum
import json
from typing import Optional
from datetime import UTC, datetime
from flask_login import UserMixin
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .engine import db
from .types import StringUUID


class TenantAccountRole(enum.StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    NORMAL = "normal"
    DATASET_OPERATOR = "dataset_operator"

    @staticmethod
    def is_valid_role(role: str) -> bool:
        if not role:
            return False
        return role in {
            TenantAccountRole.OWNER,
            TenantAccountRole.ADMIN,
            TenantAccountRole.EDITOR,
            TenantAccountRole.NORMAL,
            TenantAccountRole.DATASET_OPERATOR,
        }

    @staticmethod
    def is_privileged_role(role: Optional["TenantAccountRole"]) -> bool:
        if not role:
            return False
        return role in {TenantAccountRole.OWNER, TenantAccountRole.ADMIN}

    @staticmethod
    def is_admin_role(role: Optional["TenantAccountRole"]) -> bool:
        if not role:
            return False
        return role == TenantAccountRole.ADMIN

    @staticmethod
    def is_non_owner_role(role: Optional["TenantAccountRole"]) -> bool:
        if not role:
            return False
        return role in {
            TenantAccountRole.ADMIN,
            TenantAccountRole.EDITOR,
            TenantAccountRole.NORMAL,
            TenantAccountRole.DATASET_OPERATOR,
        }

    @staticmethod
    def is_editing_role(role: Optional["TenantAccountRole"]) -> bool:
        if not role:
            return False
        return role in {TenantAccountRole.OWNER, TenantAccountRole.ADMIN, TenantAccountRole.EDITOR}

    @staticmethod
    def is_dataset_edit_role(role: Optional["TenantAccountRole"]) -> bool:
        if not role:
            return False
        return role in {
            TenantAccountRole.OWNER,
            TenantAccountRole.ADMIN,
            TenantAccountRole.EDITOR,
            TenantAccountRole.DATASET_OPERATOR,
        }


class AccountStatus(enum.StrEnum):
    PENDING = "pending"
    UNINITIALIZED = "uninitialized"
    ACTIVE = "active"
    BANNED = "banned"
    CLOSED = "closed"


class Account(UserMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (db.PrimaryKeyConstraint("id", name="account_pkey"), db.Index("account_email_idx", "email"))

    id: Mapped[str] = mapped_column(StringUUID, server_default=db.text("uuid_generate_v4()"))
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    password: Mapped[Optional[str]] = mapped_column(String(255))
    password_salt: Mapped[Optional[str]] = mapped_column(String(255))
    avatar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    interface_language: Mapped[Optional[str]] = mapped_column(String(255))
    interface_theme: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(255))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), server_default=db.text("'active'::character varying"))
    initialized_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)

    @property
    def is_password_set(self):
        return self.password is not None

    @property
    def current_tenant(self):
        # FIXME: fix the type error later, because the type is important maybe cause some bugs
        return self._current_tenant  # type: ignore

    @current_tenant.setter
    def current_tenant(self, value: "Tenant"):
        tenant = value
        ta = TenantAccountJoin.query.filter_by(tenant_id=tenant.id, account_id=self.id).first()
        if ta:
            tenant.current_role = ta.role
        else:
            tenant = None  # type: ignore

        self._current_tenant = tenant

    @property
    def current_tenant_id(self) -> str | None:
        return self._current_tenant.id if self._current_tenant else None

    @current_tenant_id.setter
    def current_tenant_id(self, value: str):
        try:
            tenant_account_join = (
                db.session.query(Tenant, TenantAccountJoin)
                .filter(Tenant.id == value)
                .filter(TenantAccountJoin.tenant_id == Tenant.id)
                .filter(TenantAccountJoin.account_id == self.id)
                .one_or_none()
            )

            if tenant_account_join:
                tenant, ta = tenant_account_join
                tenant.current_role = ta.role
            else:
                tenant = None
        except Exception:
            tenant = None

        self._current_tenant = tenant

    @property
    def current_role(self):
        return self._current_tenant.current_role

    def get_status(self) -> AccountStatus:
        status_str = self.status
        return AccountStatus(status_str)

    @classmethod
    def get_by_openid(cls, provider: str, open_id: str):
        account_integrate = (
            db.session.query(AccountIntegrate)
            .filter(AccountIntegrate.provider == provider, AccountIntegrate.open_id == open_id)
            .one_or_none()
        )
        if account_integrate:
            return db.session.query(Account).filter(Account.id == account_integrate.account_id).one_or_none()
        return None

    # check current_user.current_tenant.current_role in ['admin', 'owner']
    @property
    def is_admin_or_owner(self):
        return TenantAccountRole.is_privileged_role(self._current_tenant.current_role)

    @property
    def is_admin(self):
        return TenantAccountRole.is_admin_role(self._current_tenant.current_role)

    @property
    def is_editor(self):
        return TenantAccountRole.is_editing_role(self._current_tenant.current_role)

    @property
    def is_dataset_editor(self):
        return TenantAccountRole.is_dataset_edit_role(self._current_tenant.current_role)

    @property
    def is_dataset_operator(self):
        return self._current_tenant.current_role == TenantAccountRole.DATASET_OPERATOR

    @classmethod
    def get_by_email(cls, email: str):
        """通过邮箱查找用户"""
        return db.session.query(cls).filter(cls.email == email).first()

    @classmethod
    def create(cls, email: str, name: str, avatar: str = None):
        """创建新用户"""
        account = cls(
            email=email,
            name=name,
            avatar=avatar,
            interface_theme="light",
            interface_language="zh-Hans",
            timezone="Asia/Shanghai",
            status=AccountStatus.ACTIVE,
            initialized_at=datetime.now(UTC),
        )
        db.session.add(account)
        db.session.commit()
        return account


class TenantStatus(enum.StrEnum):
    NORMAL = "normal"
    ARCHIVE = "archive"


class Tenant(db.Model):
    __tablename__ = "tenants"
    __table_args__ = (db.PrimaryKeyConstraint("id", name="tenant_pkey"),)

    id = db.Column(StringUUID, server_default=db.text("uuid_generate_v4()"))
    name = db.Column(db.String(255), nullable=False)
    encrypt_public_key = db.Column(db.Text)
    plan = db.Column(db.String(255), nullable=False, server_default=db.text("'basic'::character varying"))
    status = db.Column(db.String(255), nullable=False, server_default=db.text("'normal'::character varying"))
    custom_config = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())

    def get_accounts(self) -> list[Account]:
        return (
            db.session.query(Account)
            .filter(Account.id == TenantAccountJoin.account_id, TenantAccountJoin.tenant_id == self.id)
            .all()
        )

    @property
    def custom_config_dict(self) -> dict:
        return json.loads(self.custom_config) if self.custom_config else {}

    @custom_config_dict.setter
    def custom_config_dict(self, value: dict):
        self.custom_config = json.dumps(value)


class TenantAccountJoin(db.Model): 
    __tablename__ = "tenant_account_joins"
    __table_args__ = (
        db.PrimaryKeyConstraint("id", name="tenant_account_join_pkey"),
        db.Index("tenant_account_join_account_id_idx", "account_id"),
        db.Index("tenant_account_join_tenant_id_idx", "tenant_id"),
        db.UniqueConstraint("tenant_id", "account_id", name="unique_tenant_account_join"),
    )

    id: Mapped[str] = mapped_column(StringUUID, server_default=db.text("uuid_generate_v4()"))
    tenant_id: Mapped[str] = mapped_column(StringUUID)
    account_id: Mapped[str] = mapped_column(StringUUID)
    current: Mapped[bool] = mapped_column(db.Boolean, server_default=db.text("false"))
    role: Mapped[str] = mapped_column(String(16), server_default="normal")
    invited_by: Mapped[Optional[str]] = mapped_column(StringUUID)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    @classmethod
    def create(cls, tenant_id: str, account_id: str, role: str):
        tenant_account_join = cls(
            tenant_id=tenant_id,
            account_id=account_id,
            role=role
        )
        db.session.add(tenant_account_join)
        db.session.commit()
        return tenant_account_join

    @classmethod
    def get_by_account(cls, tenant_id: str, account_id: str):
        """通过账号查找用户"""
        return db.session.query(cls).filter(cls.tenant_id == tenant_id, cls.account_id == account_id).first()

class AccountIntegrate(Base):
    __tablename__ = "account_integrates"
    __table_args__ = (
        db.PrimaryKeyConstraint("id", name="account_integrate_pkey"),
        db.UniqueConstraint("account_id", "provider", name="unique_account_provider"),
        db.UniqueConstraint("provider", "open_id", name="unique_provider_open_id"),
    )

    id: Mapped[str] = mapped_column(StringUUID, server_default=db.text("uuid_generate_v4()"))
    account_id: Mapped[str] = mapped_column(StringUUID)
    provider: Mapped[str] = mapped_column(String(16))
    open_id: Mapped[str] = mapped_column(String(255))
    encrypted_token: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
