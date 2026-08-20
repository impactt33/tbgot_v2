from enum import Enum


class PostStatus(Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"