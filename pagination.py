"""Reusable pagination helper for database query results."""
import math


class Pagination:
    """Helper class to calculate pagination metadata and page link sequences."""

    def __init__(self, page, per_page, total_items, args=None):
        self.per_page = max(1, int(per_page))
        self.total_items = max(0, int(total_items))
        self.total_pages = max(1, math.ceil(self.total_items / self.per_page))
        p = int(page or 1)
        if p < 1:
            p = 1
        elif p > self.total_pages:
            p = self.total_pages
        self.page = p
        self.args = dict(args or {})

    @property
    def offset(self):
        return (self.page - 1) * self.per_page

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.total_pages

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def next_num(self):
        return self.page + 1

    @property
    def start_index(self):
        return min((self.page - 1) * self.per_page + 1, self.total_items) if self.total_items else 0

    @property
    def end_index(self):
        return min(self.page * self.per_page, self.total_items)

    def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
        last = 0
        for num in range(1, self.total_pages + 1):
            if (
                num <= left_edge
                or (self.page - left_current <= num <= self.page + right_current)
                or num > self.total_pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num
