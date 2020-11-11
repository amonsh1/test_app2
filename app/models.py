from enum import Enum

from pydantic import BaseModel, validator


__all__ = ['Sort', 'Order', 'SearchQuery']


class Sort(Enum):
    ACTIVITY = 'activity'
    VOTES = 'votes'
    CREATION = 'creation'


class Order(Enum):
    ASC = 'asc'
    DESC = 'desc'


class SearchQuery(BaseModel):
    page: int
    pagesize: int
    intitle: str
    sort: Sort
    order: Order

    @validator('page')
    def page_must_be_positive(cls, v):
        if v < 1:
            raise ValueError('Номер страницы не может быть отрицательным')
        return v

    @validator('pagesize')
    def pagesize_max_value(cls, v):
        if v > 100:
            raise ValueError('Максимальный размер страницы - 100')
        return v
