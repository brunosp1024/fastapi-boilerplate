from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base
from app.db.models.mixins import AuditMixin, BaseMixin


class Post(BaseMixin, AuditMixin, Base):
    __tablename__ = "post"

    title: Mapped[str] = mapped_column(String(30))
    text: Mapped[str] = mapped_column(String(63206))
    media_url: Mapped[str | None] = mapped_column(String, default=None)
