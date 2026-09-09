from sqlalchemy import Column, Float, String

from app.core.database import Base


class RevokedToken(Base):
    __tablename__ = "token_blacklist"

    jti = Column(String, primary_key=True)
    expires_at = Column(Float, nullable=False, default=0)
