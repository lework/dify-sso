from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.libs.helper import generate_string
from .base import Base
from .engine import db
from .types import StringUUID


class Site(Base):
    __tablename__ = "sites"
    __table_args__ = (
        db.PrimaryKeyConstraint("id", name="site_pkey"),
        db.Index("site_app_id_idx", "app_id"),
        db.Index("site_code_idx", "code", "status"),
    )

    id = mapped_column(StringUUID, server_default=db.text("uuid_generate_v4()"))
    app_id = mapped_column(StringUUID, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    icon_type = mapped_column(String(255), nullable=True)
    icon = mapped_column(String(255))
    icon_background = mapped_column(String(255))
    description = mapped_column(db.Text)
    default_language: Mapped[str] = mapped_column(String(255), nullable=False)
    chat_color_theme = mapped_column(String(255))
    chat_color_theme_inverted: Mapped[bool] = mapped_column(db.Boolean, nullable=False, server_default=db.text("false"))
    copyright = mapped_column(String(255))
    privacy_policy = mapped_column(String(255))
    show_workflow_steps: Mapped[bool] = mapped_column(db.Boolean, nullable=False, server_default=db.text("true"))
    use_icon_as_answer_icon: Mapped[bool] = mapped_column(db.Boolean, nullable=False, server_default=db.text("false"))
    _custom_disclaimer: Mapped[str] = mapped_column("custom_disclaimer", db.TEXT, default="")
    customize_domain = mapped_column(String(255))
    customize_token_strategy: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_public: Mapped[bool] = mapped_column(db.Boolean, nullable=False, server_default=db.text("false"))
    status = mapped_column(String(255), nullable=False, server_default=db.text("'normal'::character varying"))
    created_by = mapped_column(StringUUID, nullable=True)
    created_at = mapped_column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    updated_by = mapped_column(StringUUID, nullable=True)
    updated_at = mapped_column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    code = mapped_column(String(255))

    @property
    def custom_disclaimer(self):
        return self._custom_disclaimer

    @custom_disclaimer.setter
    def custom_disclaimer(self, value: str):
        if len(value) > 512:
            raise ValueError("Custom disclaimer cannot exceed 512 characters.")
        self._custom_disclaimer = value

    @staticmethod
    def generate_code(n):
        while True:
            result = generate_string(n)
            while db.session.query(Site).where(Site.code == result).count() > 0:
                result = generate_string(n)

            return result