import datetime
import calendar

from base import BaseHandler



class HistoryCalendar(calendar.Calendar):
    # CSS classes for the day <td>s
    cssclasses = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    def formatday(self, date, current_date):
        """
        Return a day as a table cell.
        """
        if date is None:
            return '<td class="noday">&nbsp;</td>' # day outside month
        else:
            weekday = date.weekday()
            print date,current_date
            if date==current_date:
                cell = '<td class="current">%s</td>' % (date.day,)
            else:
                cell = '<td><a href="/%s">%s</a></td>' % (date.strftime('%Y-%m-%d'),date.day)
            return cell

    def formatweek(self, theweek, current_date):
        """
        Return a complete week as a table row.
        """
        s = ''.join(self.formatday(d,current_date) for d in theweek)
        return '<tr>%s</tr>' % s

    def formatweekday(self, day):
        """
        Return a weekday name as a table header.
        """
        return '<th class="%s">%s</th>' % (self.cssclasses[day], calendar.day_abbr[day])

    def formatweekheader(self):
        """
        Return a header for a week as a table row.
        """
        s = ''.join(self.formatweekday(i) for i in self.iterweekdays())
        return '<tr>%s</tr>' % s

    def formatmonthname(self, theyear, themonth, withyear=True):
        """
        Return a month name as a table row.
        """
        if withyear:
            s = '%s %s' % (calendar.month_name[themonth], theyear)
        else:
            s = '%s' % calendar.month_name[themonth]
        return '<tr><th colspan="7" class="month">%s</th></tr>' % s

    def formatmonth(self, theyear, themonth, current_date=None):
        """
        Return a formatted month as a table.
        """
        withyear = False
        v = []
        a = v.append
        a('<table border="0" cellpadding="0" cellspacing="0" class="month">')
        a('\n')
        a(self.formatmonthname(theyear, themonth, withyear=withyear))
        a('\n')
        a(self.formatweekheader())
        a('\n')
        for week in self.monthdatescalendar(theyear, themonth):
            # replace days outside month with None
            week = [d if (d.year==theyear and d.month == themonth) else None for d in week]
            a(self.formatweek(week,current_date))
            a('\n')
        a('</table>')
        a('\n')
        return ''.join(v)



class HistoryHandler(BaseHandler):
    """show summary for a given day"""
    def get(self,datestr):
        date = datetime.datetime.strptime(datestr,'%Y-%m-%d').date()
        arts = self.store.art_get_by_date(date)
        cal = HistoryCalendar()
        self.render('history.html', date=date, arts=arts, cal=cal)

