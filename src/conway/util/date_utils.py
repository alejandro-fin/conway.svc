import datetime                                             as _dt
from zoneinfo                                               import ZoneInfo as _ZoneInfo


class DateUtils():

    def __init__(self):
        '''
        '''

    def to_ccl_timezone(self, some_date):
        '''
        Changes the timezone of `some_date` to be the standard timezone for CCL (i.e., California) and returns
        the modified datetime object.

        :param datetime some_date: original datetime object in possibly some non-CCL timezone
        :returns: the equivalent datetime as `some_date` but in the CCL timezone
        :rtype: datetime
        '''
        original_tz                         = some_date.tzinfo
        ccl_tz                              = _ZoneInfo('America/Los_Angeles')
        converted_date                      = some_date.replace(tzinfo=original_tz).astimezone(tz=ccl_tz)
        return converted_date