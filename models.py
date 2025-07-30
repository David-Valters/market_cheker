from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, REAL, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


class Config(Base):
    __tablename__ = 'config'

    value: Mapped[str] = mapped_column(Text)
    key: Mapped[Optional[str]] = mapped_column(Text, primary_key=True)


class Skins(Base):
    __tablename__ = 'skins'

    skin_id: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    id: Mapped[Optional[int]] = mapped_column(Integer, primary_key=True)
    price: Mapped[Optional[float]] = mapped_column(REAL)
    last_updated: Mapped[Optional[str]] = mapped_column(Text)
    icon_url: Mapped[Optional[str]] = mapped_column(Text)


class Lot(Base):
    __tablename__ = 'lots'

    lot_id: Mapped[str] = mapped_column(String, primary_key=True)
    skin_id: Mapped[str] = mapped_column(ForeignKey('top_lots.skin_id', ondelete='CASCADE'))
    price: Mapped[float] = mapped_column(Float)
    serial: Mapped[str] = mapped_column(String)

    def __repr__(self):
        return f"<Lot id={self.lot_id}, price={self.price}, serial={self.serial}>"