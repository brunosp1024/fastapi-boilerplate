from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.mixins import BaseMixin


class PostBase(BaseModel):
    title: Annotated[
        str, Field(min_length=2, max_length=30, examples=["This is my post"])
    ]
    text: Annotated[
        str,
        Field(
            min_length=1, max_length=63206, examples=["This is the content of my post."]
        ),
    ]
    media_url: Annotated[
        str | None,
        Field(
            pattern=r"^(https?|ftp)://[^\s/$.?#].[^^\s]*$",
            examples=["https://www.postimageurl.com"],
            default=None,
        ),
    ]


class PostRead(PostBase, BaseMixin):
    pass


class PostCreate(PostBase):
    model_config = ConfigDict(extra="forbid")


class PostUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[
        str | None,
        Field(
            min_length=2,
            max_length=30,
            examples=["This is my updated post"],
            default=None,
        ),
    ]
    text: Annotated[
        str | None,
        Field(
            min_length=1,
            max_length=63206,
            examples=["This is the updated content of my post."],
            default=None,
        ),
    ]
    media_url: Annotated[
        str | None,
        Field(
            pattern=r"^(https?|ftp)://[^\s/$.?#].[^\s]*$",
            examples=["https://www.postimageurl.com"],
            default=None,
        ),
    ]


class PostDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deleted_at: datetime
