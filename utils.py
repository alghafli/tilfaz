import datetime
import calendar
from dateutil import rrule

N_ = lambda word: word

wd = [N_('mon'), N_('tue'), N_('wed'), N_('thu'), N_('fri'), N_('sat'), N_('sun')]

class Weekdays:
    def __init__(self, time, day1, *args):
        args = (day1,) + args
        for c in args:
            if type(c) is not int or not 0 <= c <= 6:
                raise ValueError('all arguments must be integers between 0 and 6')
        
        self._time = datetime.time(hour=time.hour, minute=time.minute)
        self._days = tuple(sorted(set(args)))
    
    @property
    def time(self):
        return self._time
    
    @property
    def days(self):
        return self._days
    
    def next_time(self, time=None):
        if time is None:
            time = datetime.datetime.now()
        
        time = time + datetime.timedelta(seconds=60)
        time = time.replace(second=0, microsecond=0)
        new_time = rrule.rrule(freq=rrule.WEEKLY, byweekday=self.days, count=1,
            dtstart=time, byhour=self.time.hour, byminute=self.time.minute, bysecond=0)
        return new_time[0]
    
    def next_day(self, time, weekday):
        days_ahead = weekday - time.weekday()
        new_time = time + datetime.timedelta(days=days_ahead)
        new_time = datetime.datetime.combine(new_time, self.time)
        if new_time <= time:
            new_time += datetime.timedelta(days=7)
        
        return new_time
    
    def __repr__(self):
        return '{}({}) @ {}'.format(type(self).__name__, ','.join([str(c) for c in self.days]), self.time)
    
    def __str__(self):
        return '{},{:%H:%M},{}'.format('weekdays', self.time, list(self.days))

class Monthdays:
    def __init__(self, time, day1, *args):
        args = (day1,) + args
        for c in args:
            if type(c) is not int or not 1 <= c <= 31:
                raise ValueError('all arguments must be integers between 0 and 31')
        self._time = datetime.time(hour=time.hour, minute=time.minute)
        self._days = tuple(sorted(set(args)))
    
    @property
    def time(self):
        return self._time
    
    @property
    def days(self):
        return self._days
    
    def next_time(self, time=None):
        if time is None:
            time = datetime.datetime.now()
        
        new_minute = (time.minute+1) % 60
        new_hour = time.hour + time.minute // 60
        time = time.replace(hour=new_hour, minute=new_minute, second=0, microsecond=0)
        new_time = rrule.rrule(freq=rrule.MONTHLY, bymonthday=self.days + (-1,),
            count=2, dtstart=time, byhour=self.time.hour,
            byminute=self.time.minute, bysecond=0)
        if new_time[0].day in self.days or new_time[0].day not in self.days and new_time[0].day < max(self.days):
            new_time = new_time[0]
        else:
            new_time = new_time[1]
        
        return new_time
    
    def next_day(self, date, monthday):
        new_date = self.set_day(date, monthday)
        new_date = datetime.datetime.combine(new_date, self.time)
        if new_date <= date:
            new_date = self.next_month(new_date)
        
        return new_date
    
    def next_month(self, date):
        year = date.year
        month = date.month + 1
        day = date.day
        if month > 12:
            year += 1
            month = 1
        
        date = self.set_day(date.replace(year=year, month=month, day=1), day)
        
        return date
    
    def set_day(self, date, day):
        if day > calendar.monthrange(date.year, date.month)[1]:
            date = self.next_month(date.replace(day=1))
        else:
            date = date.replace(day=day)
        
        return date
    
    def __repr__(self):
        return '{}({}) @ {}'.format(type(self).__name__, ','.join([str(c) for c in self.days]), self.time)
    
    def __str__(self):
        return '{},{:%H:%M},{}'.format('monthdays', self.time, list(self.days))
