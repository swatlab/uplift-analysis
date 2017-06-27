import csv
import locale
from datetime import datetime
from dateutil import relativedelta
from libmozdata.utils import as_utc
import get_bugs
import utils

# The month abbreviation should be in English.
locale.setlocale(locale.LC_TIME, 'C')

if __name__ == '__main__':
    bugs = get_bugs.get_all()
    uplifts = utils.get_uplifts(bugs)

    months = {}

    for uplift in uplifts:
        for channel in utils.uplift_approved_channels(uplift):
            uplift_date = utils.get_uplift_date(uplift, channel)
            if uplift_date > as_utc(datetime(2016, 8, 24)):
                continue
            delta = relativedelta.relativedelta(uplift_date, as_utc(datetime(2014, 7, 1)))
            delta_num = delta.years * 12 + delta.months
            key = (delta_num, uplift_date.strftime('%b %Y'), channel)
            if key not in months:
                months[key] = 0
            months[key] += 1

    with open('uplift_dates.csv', 'w') as output_file:
        csv_writer = csv.writer(output_file)
        csv_writer.writerow(['Delta', 'Month', 'Channel', 'Number_of_uplifts'])
        for (delta_str, month, channel), number in sorted(months.items(), key=lambda x: x[0][0]):
            csv_writer.writerow([delta_str, month, channel, number])
