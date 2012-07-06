
class Paginator:
    """ paginator object for wrapping an sqlalchemy query """

    def __init__(self, query=None, per_page=100, current_page=0, page_url_fn=None):
        self.query = query
        self.per_page = per_page
        self.cur = current_page
        self._total_items = None
        self.page_url = page_url_fn

    @property
    def items(self):
        if self.query is None:
            return []
        return self.query.\
            offset((self.cur-1)*self.per_page).\
            limit(self.per_page).\
            all()

    @property
    def total_items(self):
        if self.query is None:
            return 0
        if self._total_items is None:
            self._total_items = self.query.count()
        return self._total_items


    @property
    def total_pages(self):
        return (max(0,self.total_items-1) // self.per_page)+1;

    def __iter__(self):
        """ helper for rendering: step over the page numbers, returning None where should be a gap """
        MID_PAD=3
        END_PAD=2

        mid=(max(1,self.cur-MID_PAD), min(self.cur+MID_PAD, self.total_pages)+1)
        left=(1, min(END_PAD+1, mid[0]))
        right=(max((self.total_pages+1)-END_PAD, mid[1]), self.total_pages+1)

        for p in range(left[0],left[1]):
            yield p
        if mid[0]>left[1]:
            yield None  # a gap
        for p in range(mid[0],mid[1]):
            yield p
        if right[0]>mid[1]:
            yield None  # a gap
        for p in range(right[0],right[1]):
            yield p


    @property
    def previous(self):
        """ return previous page number (or None)"""
        if self.cur>1:
            return self.cur-1
        else:
            return None

    @property
    def next(self):
        """ return next page number (or None)"""
        if self.cur<self.total_pages:
            return self.cur+1
        else:
            return None

