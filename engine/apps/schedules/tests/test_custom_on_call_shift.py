from calendar import monthrange

import pytest
from django.utils import timezone

from apps.schedules.ical_utils import list_users_to_notify_from_ical
from apps.schedules.models import CustomOnCallShift, OnCallSchedule, OnCallScheduleCalendar, OnCallScheduleWeb


@pytest.mark.django_db
def test_get_on_call_users_from_single_event(make_organization_and_user, make_on_call_shift, make_schedule):
    organization, user = make_organization_and_user()

    schedule = make_schedule(organization, schedule_class=OnCallScheduleCalendar)
    date = timezone.now().replace(tzinfo=None, microsecond=0)

    data = {
        "priority_level": 1,
        "start": date,
        "rotation_start": date,
        "duration": timezone.timedelta(seconds=10800),
    }

    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_SINGLE_EVENT, **data
    )
    on_call_shift.users.add(user)

    schedule.custom_on_call_shifts.add(on_call_shift)

    # user is on-call
    date = date + timezone.timedelta(minutes=5)
    users_on_call = list_users_to_notify_from_ical(schedule, date)
    assert len(users_on_call) == 1
    assert user in users_on_call


@pytest.mark.django_db
def test_get_on_call_users_from_web_schedule_override(make_organization_and_user, make_on_call_shift, make_schedule):
    organization, user = make_organization_and_user()

    schedule = make_schedule(organization, schedule_class=OnCallScheduleWeb)
    date = timezone.now().replace(microsecond=0)

    data = {
        "start": date,
        "rotation_start": date,
        "duration": timezone.timedelta(seconds=10800),
        "schedule": schedule,
    }

    on_call_shift = make_on_call_shift(organization=organization, shift_type=CustomOnCallShift.TYPE_OVERRIDE, **data)
    on_call_shift.add_rolling_users([[user]])

    # user is on-call
    date = date + timezone.timedelta(minutes=5)
    users_on_call = list_users_to_notify_from_ical(schedule, date)
    assert len(users_on_call) == 1
    assert user in users_on_call


@pytest.mark.django_db
def test_get_on_call_users_from_recurrent_event(make_organization_and_user, make_on_call_shift, make_schedule):
    organization, user = make_organization_and_user()

    schedule = make_schedule(organization, schedule_class=OnCallScheduleCalendar)
    date = timezone.now().replace(tzinfo=None, microsecond=0)

    data = {
        "priority_level": 1,
        "start": date,
        "rotation_start": date,
        "duration": timezone.timedelta(seconds=10800),
        "frequency": CustomOnCallShift.FREQUENCY_DAILY,
        "interval": 2,
    }

    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_RECURRENT_EVENT, **data
    )
    on_call_shift.users.add(user)

    schedule.custom_on_call_shifts.add(on_call_shift)

    # user is on-call
    date = date + timezone.timedelta(minutes=5)
    users_on_call = list_users_to_notify_from_ical(schedule, date)
    assert len(users_on_call) == 1
    assert user in users_on_call

    # user is not on-call according to event recurrence rules (interval = 2)
    date = date + timezone.timedelta(days=1)
    users_on_call = list_users_to_notify_from_ical(schedule, date)
    assert len(users_on_call) == 0

    # user is on-call again
    date = date + timezone.timedelta(days=1)
    users_on_call = list_users_to_notify_from_ical(schedule, date)
    assert len(users_on_call) == 1
    assert user in users_on_call


@pytest.mark.django_db
def test_get_on_call_users_from_web_schedule_recurrent_event(
    make_organization_and_user, make_on_call_shift, make_schedule
):
    organization, user = make_organization_and_user()

    schedule = make_schedule(organization, schedule_class=OnCallScheduleWeb)
    date = timezone.now().replace(microsecond=0)

    data = {
        "priority_level": 1,
        "start": date,
        "rotation_start": date,
        "duration": timezone.timedelta(seconds=10800),
        "frequency": CustomOnCallShift.FREQUENCY_DAILY,
        "interval": 2,
        "schedule": schedule,
    }

    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_RECURRENT_EVENT, **data
    )
    on_call_shift.users.add(user)

    # user is on-call
    date = date + timezone.timedelta(minutes=5)
    users_on_call = list_users_to_notify_from_ical(schedule, date)
    assert len(users_on_call) == 1
    assert user in users_on_call

    # user is not on-call according to event recurrence rules (interval = 2)
    date = date + timezone.timedelta(days=1)
    users_on_call = list_users_to_notify_from_ical(schedule, date)
    assert len(users_on_call) == 0

    # user is on-call again
    date = date + timezone.timedelta(days=1)
    users_on_call = list_users_to_notify_from_ical(schedule, date)
    assert len(users_on_call) == 1
    assert user in users_on_call


@pytest.mark.django_db
def test_get_on_call_users_from_rolling_users_event(
    make_organization_and_user, make_user_for_organization, make_on_call_shift, make_schedule
):
    organization, user_1 = make_organization_and_user()
    user_2 = make_user_for_organization(organization)

    schedule = make_schedule(organization, schedule_class=OnCallScheduleCalendar)
    now = timezone.now().replace(microsecond=0)

    data = {
        "priority_level": 1,
        "start": now,
        "rotation_start": now,
        "duration": timezone.timedelta(seconds=10800),
        "frequency": CustomOnCallShift.FREQUENCY_DAILY,
        "interval": 2,
    }
    rolling_users = [[user_1], [user_2]]
    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_ROLLING_USERS_EVENT, **data
    )
    on_call_shift.add_rolling_users(rolling_users)
    schedule.custom_on_call_shifts.add(on_call_shift)

    date = now + timezone.timedelta(minutes=5)

    user_1_on_call_dates = [date, date + timezone.timedelta(days=4)]
    user_2_on_call_dates = [date + timezone.timedelta(days=2), date + timezone.timedelta(days=6)]
    nobody_on_call_dates = [
        date + timezone.timedelta(days=1),
        date + timezone.timedelta(days=3),
        date + timezone.timedelta(days=5),
    ]

    for date in user_1_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, date)
        assert len(users_on_call) == 1
        assert user_1 in users_on_call

    for date in user_2_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, date)
        assert len(users_on_call) == 1
        assert user_2 in users_on_call

    for date in nobody_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, date)
        assert len(users_on_call) == 0


@pytest.mark.django_db
def test_rolling_users_event_with_interval_hourly(
    make_organization_and_user, make_user_for_organization, make_on_call_shift, make_schedule
):
    organization, user_1 = make_organization_and_user()
    user_2 = make_user_for_organization(organization)

    schedule = make_schedule(organization, schedule_class=OnCallScheduleWeb)
    now = timezone.now().replace(microsecond=0)

    data = {
        "priority_level": 1,
        "start": now,
        "rotation_start": now + timezone.timedelta(hours=1),
        "duration": timezone.timedelta(seconds=600),
        "frequency": CustomOnCallShift.FREQUENCY_HOURLY,
        "interval": 2,
        "schedule": schedule,
    }
    rolling_users = [[user_1], [user_2]]
    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_ROLLING_USERS_EVENT, **data
    )
    on_call_shift.add_rolling_users(rolling_users)

    date = now + timezone.timedelta(minutes=5)

    user_1_on_call_dates = [date + timezone.timedelta(hours=4)]
    user_2_on_call_dates = [date + timezone.timedelta(hours=2), date + timezone.timedelta(hours=6)]
    nobody_on_call_dates = [
        date,
        date + timezone.timedelta(hours=1),
        date + timezone.timedelta(hours=3),
        date + timezone.timedelta(hours=5),
    ]

    for dt in user_1_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_1 in users_on_call

    for dt in user_2_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_2 in users_on_call

    for date in nobody_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, date)
        assert len(users_on_call) == 0


@pytest.mark.django_db
def test_rolling_users_event_with_interval_daily(
    make_organization_and_user, make_user_for_organization, make_on_call_shift, make_schedule
):
    organization, user_1 = make_organization_and_user()
    user_2 = make_user_for_organization(organization)

    schedule = make_schedule(organization, schedule_class=OnCallScheduleWeb)
    now = timezone.now().replace(microsecond=0)

    data = {
        "priority_level": 1,
        "start": now,
        "rotation_start": now,
        "duration": timezone.timedelta(seconds=10800),
        "frequency": CustomOnCallShift.FREQUENCY_DAILY,
        "interval": 2,
        "schedule": schedule,
    }
    rolling_users = [[user_1], [user_2]]
    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_ROLLING_USERS_EVENT, **data
    )
    on_call_shift.add_rolling_users(rolling_users)

    date = now + timezone.timedelta(minutes=5)

    user_1_on_call_dates = [date, date + timezone.timedelta(days=4)]
    user_2_on_call_dates = [date + timezone.timedelta(days=2), date + timezone.timedelta(days=6)]
    nobody_on_call_dates = [
        date + timezone.timedelta(days=1),
        date + timezone.timedelta(days=3),
        date + timezone.timedelta(days=5),
    ]

    for dt in user_1_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_1 in users_on_call

    for dt in user_2_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_2 in users_on_call

    for dt in nobody_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 0


@pytest.mark.django_db
def test_rolling_users_event_with_interval_weekly(
    make_organization_and_user, make_user_for_organization, make_on_call_shift, make_schedule
):
    organization, user_1 = make_organization_and_user()
    user_2 = make_user_for_organization(organization)

    schedule = make_schedule(organization, schedule_class=OnCallScheduleCalendar)
    now = timezone.now().replace(microsecond=0)

    data = {
        "priority_level": 1,
        "start": now,
        "rotation_start": now + timezone.timedelta(hours=1),
        "duration": timezone.timedelta(seconds=10800),
        "frequency": CustomOnCallShift.FREQUENCY_WEEKLY,
        "interval": 2,
        "week_start": now.weekday(),
        "schedule": schedule,
    }
    rolling_users = [[user_1], [user_2]]
    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_ROLLING_USERS_EVENT, **data
    )
    on_call_shift.add_rolling_users(rolling_users)
    schedule.custom_on_call_shifts.add(on_call_shift)

    date = now + timezone.timedelta(minutes=5)

    user_1_on_call_dates = [date + timezone.timedelta(days=28)]
    user_2_on_call_dates = [date + timezone.timedelta(days=14), date + timezone.timedelta(days=42)]
    nobody_on_call_dates = [
        date,
        date + timezone.timedelta(days=7),
        date + timezone.timedelta(days=21),
        date + timezone.timedelta(days=35),
    ]

    for dt in user_1_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_1 in users_on_call

    for dt in user_2_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_2 in users_on_call

    for dt in nobody_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 0


@pytest.mark.django_db
def test_rolling_users_event_with_interval_monthly(
    make_organization_and_user, make_user_for_organization, make_on_call_shift, make_schedule
):
    organization, user_1 = make_organization_and_user()
    user_2 = make_user_for_organization(organization)

    schedule = make_schedule(organization, schedule_class=OnCallScheduleCalendar)
    start_date = timezone.now().replace(day=1, microsecond=0)
    days_for_next_month_1 = monthrange(start_date.year, start_date.month)[1]
    days_for_next_month_2 = monthrange(start_date.year, start_date.month + 1)[1] + days_for_next_month_1
    days_for_next_month_3 = monthrange(start_date.year, start_date.month + 2)[1] + days_for_next_month_2
    days_for_next_month_4 = monthrange(start_date.year, start_date.month + 3)[1] + days_for_next_month_3

    data = {
        "priority_level": 1,
        "start": start_date,
        "rotation_start": start_date + timezone.timedelta(hours=1),
        "duration": timezone.timedelta(seconds=10800),
        "frequency": CustomOnCallShift.FREQUENCY_MONTHLY,
        "interval": 2,
        "week_start": start_date.weekday(),
        "schedule": schedule,
    }
    rolling_users = [[user_1], [user_2]]
    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_ROLLING_USERS_EVENT, **data
    )
    on_call_shift.add_rolling_users(rolling_users)
    schedule.custom_on_call_shifts.add(on_call_shift)

    date = start_date + timezone.timedelta(minutes=5)

    user_1_on_call_dates = [date + timezone.timedelta(days=days_for_next_month_4)]
    user_2_on_call_dates = [date + timezone.timedelta(days=days_for_next_month_2)]
    nobody_on_call_dates = [
        date,
        date + timezone.timedelta(days=days_for_next_month_1),
        date + timezone.timedelta(days=days_for_next_month_3),
    ]

    for dt in user_1_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_1 in users_on_call

    for dt in user_2_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_2 in users_on_call

    for dt in nobody_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 0


@pytest.mark.django_db
def test_rolling_users_with_diff_start_and_rotation_start_hourly(
    make_organization_and_user, make_user_for_organization, make_on_call_shift, make_schedule
):
    organization, user_1 = make_organization_and_user()
    user_2 = make_user_for_organization(organization)
    user_3 = make_user_for_organization(organization)

    schedule = make_schedule(organization, schedule_class=OnCallScheduleWeb)
    now = timezone.now().replace(microsecond=0)

    data = {
        "priority_level": 1,
        "start": now,
        "rotation_start": now + timezone.timedelta(hours=2),
        "duration": timezone.timedelta(seconds=1800),
        "frequency": CustomOnCallShift.FREQUENCY_HOURLY,
        "schedule": schedule,
        "until": now + timezone.timedelta(hours=6, minutes=59),
    }
    rolling_users = [[user_1], [user_2], [user_3]]
    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_ROLLING_USERS_EVENT, **data
    )
    on_call_shift.add_rolling_users(rolling_users)

    date = now + timezone.timedelta(minutes=5)
    # rotation starts from user_3, because user_1 and user_2 started earlier than rotation start date
    user_1_on_call_dates = [date + timezone.timedelta(hours=3), date + timezone.timedelta(hours=6)]
    user_2_on_call_dates = [date + timezone.timedelta(hours=4)]
    user_3_on_call_dates = [date + timezone.timedelta(hours=2), date + timezone.timedelta(hours=5)]
    nobody_on_call_dates = [
        date,  # less than rotation start
        date + timezone.timedelta(hours=1),  # less than rotation start
        date + timezone.timedelta(hours=7),  # higher than until
    ]

    for dt in user_1_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_1 in users_on_call

    for dt in user_2_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_2 in users_on_call

    for dt in user_3_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_3 in users_on_call

    for dt in nobody_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 0


@pytest.mark.django_db
def test_rolling_users_with_diff_start_and_rotation_start_daily(
    make_organization_and_user, make_user_for_organization, make_on_call_shift, make_schedule
):
    organization, user_1 = make_organization_and_user()
    user_2 = make_user_for_organization(organization)
    user_3 = make_user_for_organization(organization)

    schedule = make_schedule(organization, schedule_class=OnCallScheduleWeb)
    now = timezone.now().replace(microsecond=0)

    data = {
        "priority_level": 1,
        "start": now,
        "rotation_start": now + timezone.timedelta(days=1, hours=1),
        "duration": timezone.timedelta(seconds=1800),
        "frequency": CustomOnCallShift.FREQUENCY_DAILY,
        "schedule": schedule,
        "until": now + timezone.timedelta(days=6, minutes=1),
    }
    rolling_users = [[user_1], [user_2], [user_3]]
    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_ROLLING_USERS_EVENT, **data
    )
    on_call_shift.add_rolling_users(rolling_users)

    date = now + timezone.timedelta(minutes=5)
    # rotation starts from user_3, because user_1 and user_2 started earlier than rotation start date
    user_1_on_call_dates = [date + timezone.timedelta(days=3), date + timezone.timedelta(days=6)]
    user_2_on_call_dates = [date + timezone.timedelta(days=4)]
    user_3_on_call_dates = [date + timezone.timedelta(days=2), date + timezone.timedelta(days=5)]
    nobody_on_call_dates = [
        date,  # less than rotation start
        date + timezone.timedelta(days=1),  # less than rotation start
        date + timezone.timedelta(days=7),  # higher than until
    ]

    for dt in user_1_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_1 in users_on_call

    for dt in user_2_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_2 in users_on_call

    for dt in user_3_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_3 in users_on_call

    for dt in nobody_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 0


@pytest.mark.django_db
def test_rolling_users_with_diff_start_and_rotation_start_weekly(
    make_organization_and_user, make_user_for_organization, make_on_call_shift, make_schedule
):
    organization, user_1 = make_organization_and_user()
    user_2 = make_user_for_organization(organization)
    user_3 = make_user_for_organization(organization)

    schedule = make_schedule(organization, schedule_class=OnCallScheduleWeb)
    now = timezone.now().replace(microsecond=0)

    data = {
        "priority_level": 1,
        "start": now,
        "week_start": now.weekday(),
        "rotation_start": now + timezone.timedelta(days=7, hours=1),
        "duration": timezone.timedelta(seconds=1800),
        "frequency": CustomOnCallShift.FREQUENCY_WEEKLY,
        "schedule": schedule,
        "until": now + timezone.timedelta(days=42, minutes=1),
    }
    rolling_users = [[user_1], [user_2], [user_3]]
    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_ROLLING_USERS_EVENT, **data
    )
    on_call_shift.add_rolling_users(rolling_users)

    date = now + timezone.timedelta(minutes=5)
    # rotation starts from user_3, because user_1 and user_2 started earlier than rotation start date
    user_1_on_call_dates = [date + timezone.timedelta(days=21), date + timezone.timedelta(days=42)]
    user_2_on_call_dates = [date + timezone.timedelta(days=28)]
    user_3_on_call_dates = [date + timezone.timedelta(days=14), date + timezone.timedelta(days=35)]
    nobody_on_call_dates = [
        date,  # less than rotation start
        date + timezone.timedelta(days=7),  # less than rotation start
        date + timezone.timedelta(days=43),  # higher than until
    ]

    for dt in user_1_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_1 in users_on_call

    for dt in user_2_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_2 in users_on_call

    for dt in user_3_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_3 in users_on_call

    for dt in nobody_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 0


@pytest.mark.django_db
def test_rolling_users_with_diff_start_and_rotation_start_weekly_by_day(
    make_organization_and_user, make_user_for_organization, make_on_call_shift, make_schedule
):
    organization, user_1 = make_organization_and_user()
    user_2 = make_user_for_organization(organization)
    user_3 = make_user_for_organization(organization)

    schedule = make_schedule(organization, schedule_class=OnCallScheduleWeb)
    now = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_weekday = now.weekday()
    next_week_monday = now + timezone.timedelta(days=(0 - today_weekday) % 7)
    # SAT, SUN
    weekdays = [5, 6]
    by_day = [CustomOnCallShift.ICAL_WEEKDAY_MAP[day] for day in weekdays]

    data = {
        "priority_level": 1,
        "start": now,
        "week_start": 0,
        "rotation_start": next_week_monday,
        "duration": timezone.timedelta(seconds=1800),
        "frequency": CustomOnCallShift.FREQUENCY_WEEKLY,
        "schedule": schedule,
        "until": next_week_monday + timezone.timedelta(days=30, minutes=1),
        "by_day": by_day,
    }
    rolling_users = [[user_1], [user_2], [user_3]]
    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_ROLLING_USERS_EVENT, **data
    )
    on_call_shift.add_rolling_users(rolling_users)

    first_sat = next_week_monday + timezone.timedelta(days=5) + timezone.timedelta(minutes=5)

    user_1_on_call_dates = [first_sat + timezone.timedelta(days=15)]
    user_2_on_call_dates = [first_sat, first_sat + timezone.timedelta(days=22)]
    user_3_on_call_dates = [first_sat + timezone.timedelta(days=7), first_sat + timezone.timedelta(days=8)]
    nobody_on_call_dates = [
        now,  # less than rotation start
        first_sat - timezone.timedelta(days=7),  # before rotation start
        first_sat + timezone.timedelta(days=9),  # weekday value not in by_day
        first_sat + timezone.timedelta(days=30),  # higher than until
    ]

    for dt in user_1_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_1 in users_on_call

    for dt in user_2_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_2 in users_on_call

    for dt in user_3_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_3 in users_on_call

    for dt in nobody_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 0


@pytest.mark.django_db
def test_rolling_users_with_diff_start_and_rotation_start_monthly(
    make_organization_and_user, make_user_for_organization, make_on_call_shift, make_schedule
):
    organization, user_1 = make_organization_and_user()
    user_2 = make_user_for_organization(organization)
    user_3 = make_user_for_organization(organization)

    schedule = make_schedule(organization, schedule_class=OnCallScheduleWeb)
    now = timezone.now().replace(day=1, microsecond=0)
    days_in_curr_month = monthrange(now.year, now.month)[1]
    days_in_next_month = monthrange(now.year, now.month + 1)[1]

    data = {
        "priority_level": 1,
        "start": now,
        "week_start": now.weekday(),
        "rotation_start": now + timezone.timedelta(days=days_in_curr_month - 1, hours=1),
        "duration": timezone.timedelta(seconds=1800),
        "frequency": CustomOnCallShift.FREQUENCY_MONTHLY,
        "schedule": schedule,
        "until": now + timezone.timedelta(days=days_in_curr_month + days_in_next_month + 10, minutes=1),
    }
    rolling_users = [[user_1], [user_2], [user_3]]
    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_ROLLING_USERS_EVENT, **data
    )
    on_call_shift.add_rolling_users(rolling_users)

    date = now + timezone.timedelta(minutes=5)
    # rotation starts from user_2, because user_1 started earlier than rotation start date
    user_2_on_call_dates = [date + timezone.timedelta(days=days_in_curr_month)]
    user_3_on_call_dates = [date + timezone.timedelta(days=days_in_curr_month + days_in_next_month)]
    nobody_on_call_dates = [
        date,  # less than rotation start
        date + timezone.timedelta(days=days_in_curr_month - 1),  # less than rotation start
        date + timezone.timedelta(days=days_in_curr_month + 1),  # higher than event end
        date + timezone.timedelta(days=days_in_curr_month + days_in_next_month + 2),  # higher than event end
        date + timezone.timedelta(days=days_in_curr_month + days_in_next_month + 11),  # higher than until
    ]

    for dt in user_2_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_2 in users_on_call

    for dt in user_3_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_3 in users_on_call

    for dt in nobody_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 0


@pytest.mark.django_db
def test_rolling_users_with_diff_start_and_rotation_start_monthly_by_monthday(
    make_organization_and_user, make_user_for_organization, make_on_call_shift, make_schedule
):
    organization, user_1 = make_organization_and_user()
    user_2 = make_user_for_organization(organization)
    user_3 = make_user_for_organization(organization)

    schedule = make_schedule(organization, schedule_class=OnCallScheduleWeb)
    start_date = timezone.now().replace(day=1, microsecond=0)
    days_in_curr_month = monthrange(start_date.year, start_date.month)[1]
    days_in_next_month = monthrange(start_date.year, start_date.month + 1)[1]

    data = {
        "priority_level": 1,
        "start": start_date,
        "week_start": start_date.weekday(),
        "rotation_start": start_date + timezone.timedelta(days=days_in_curr_month - 1, hours=1),
        "duration": timezone.timedelta(seconds=1800),
        "frequency": CustomOnCallShift.FREQUENCY_MONTHLY,
        "schedule": schedule,
        "until": start_date + timezone.timedelta(days=days_in_curr_month + days_in_next_month + 10, minutes=1),
        "by_monthday": [i for i in range(1, 5)],
    }
    rolling_users = [[user_1], [user_2], [user_3]]
    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_ROLLING_USERS_EVENT, **data
    )
    on_call_shift.add_rolling_users(rolling_users)

    date = start_date + timezone.timedelta(minutes=5)
    # rotation starts from user_2, because user_1 started earlier than rotation start date
    user_2_on_call_dates = [
        date + timezone.timedelta(days=days_in_curr_month),
        date + timezone.timedelta(days=days_in_curr_month + 1),
        date + timezone.timedelta(days=days_in_curr_month + 2),
        date + timezone.timedelta(days=days_in_curr_month + 3),
    ]
    user_3_on_call_dates = [
        date + timezone.timedelta(days=days_in_curr_month + days_in_next_month),
        date + timezone.timedelta(days=days_in_curr_month + days_in_next_month + 1),
        date + timezone.timedelta(days=days_in_curr_month + days_in_next_month + 2),
        date + timezone.timedelta(days=days_in_curr_month + days_in_next_month + 3),
    ]
    nobody_on_call_dates = [
        date,  # less than rotation start
        date + timezone.timedelta(days=3),  # less than rotation start
        date + timezone.timedelta(days=days_in_curr_month + 4),  # out of by_monthday range
        date + timezone.timedelta(days=days_in_curr_month + 6),  # out of by_monthday range
        date + timezone.timedelta(days=days_in_curr_month + 10),  # out of by_monthday range
        date + timezone.timedelta(days=days_in_curr_month + days_in_next_month + 11),  # higher than until
    ]

    for dt in user_2_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_2 in users_on_call

    for dt in user_3_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 1
        assert user_3 in users_on_call

    for dt in nobody_on_call_dates:
        users_on_call = list_users_to_notify_from_ical(schedule, dt)
        assert len(users_on_call) == 0


@pytest.mark.django_db
def test_get_oncall_users_for_empty_schedule(
    make_organization,
    make_schedule,
):
    organization = make_organization()

    schedule = make_schedule(organization, schedule_class=OnCallScheduleCalendar)
    schedules = OnCallSchedule.objects.filter(pk=schedule.pk)

    assert schedules.get_oncall_users() == []


@pytest.mark.django_db
def test_get_oncall_users_for_multiple_schedules(
    make_organization,
    make_user_for_organization,
    make_on_call_shift,
    make_schedule,
):
    organization = make_organization()

    user_1 = make_user_for_organization(organization)
    user_2 = make_user_for_organization(organization)
    user_3 = make_user_for_organization(organization)

    schedule_1 = make_schedule(organization, schedule_class=OnCallScheduleCalendar)
    schedule_2 = make_schedule(organization, schedule_class=OnCallScheduleCalendar)

    now = timezone.now().replace(tzinfo=None, microsecond=0)

    on_call_shift_1 = make_on_call_shift(
        organization=organization,
        shift_type=CustomOnCallShift.TYPE_SINGLE_EVENT,
        priority_level=1,
        start=now,
        rotation_start=now,
        duration=timezone.timedelta(minutes=30),
    )

    on_call_shift_2 = make_on_call_shift(
        organization=organization,
        shift_type=CustomOnCallShift.TYPE_SINGLE_EVENT,
        priority_level=1,
        start=now,
        rotation_start=now,
        duration=timezone.timedelta(minutes=10),
    )

    on_call_shift_3 = make_on_call_shift(
        organization=organization,
        shift_type=CustomOnCallShift.TYPE_SINGLE_EVENT,
        priority_level=1,
        start=now + timezone.timedelta(minutes=10),
        rotation_start=now + timezone.timedelta(minutes=10),
        duration=timezone.timedelta(minutes=30),
    )

    on_call_shift_1.users.add(user_1)
    on_call_shift_1.users.add(user_2)

    on_call_shift_2.users.add(user_2)

    on_call_shift_3.users.add(user_3)

    schedule_1.custom_on_call_shifts.add(on_call_shift_1)

    schedule_2.custom_on_call_shifts.add(on_call_shift_2)
    schedule_2.custom_on_call_shifts.add(on_call_shift_3)

    schedules = OnCallSchedule.objects.filter(pk__in=[schedule_1.pk, schedule_2.pk])

    expected = set(schedules.get_oncall_users(events_datetime=now + timezone.timedelta(seconds=1)))
    assert expected == {user_1, user_2}

    expected = set(schedules.get_oncall_users(events_datetime=now + timezone.timedelta(minutes=10, seconds=1)))
    assert expected == {user_1, user_2, user_3}

    assert schedules.get_oncall_users(events_datetime=now + timezone.timedelta(minutes=30, seconds=1)) == [user_3]

    assert schedules.get_oncall_users(events_datetime=now + timezone.timedelta(minutes=40, seconds=1)) == []


@pytest.mark.django_db
def test_shift_convert_to_ical(make_organization_and_user, make_on_call_shift):
    organization, user = make_organization_and_user()

    date = timezone.now().replace(tzinfo=None, microsecond=0)
    until = date + timezone.timedelta(days=30)

    data = {
        "priority_level": 1,
        "start": date,
        "rotation_start": date,
        "duration": timezone.timedelta(seconds=10800),
        "frequency": CustomOnCallShift.FREQUENCY_HOURLY,
        "interval": 1,
        "until": until,
    }

    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_RECURRENT_EVENT, **data
    )
    on_call_shift.users.add(user)

    ical_data = on_call_shift.convert_to_ical()
    ical_rrule_until = on_call_shift.until.strftime("%Y%m%dT%H%M%S")
    expected_rrule = f"RRULE:FREQ=HOURLY;UNTIL={ical_rrule_until}Z;INTERVAL=1;WKST=SU"
    assert expected_rrule in ical_data


@pytest.mark.django_db
def test_rolling_users_shift_convert_to_ical(
    make_organization_and_user,
    make_user_for_organization,
    make_on_call_shift,
):
    organization, user_1 = make_organization_and_user()
    user_2 = make_user_for_organization(organization)

    date = timezone.now().replace(microsecond=0)
    until = date + timezone.timedelta(days=30)

    data = {
        "priority_level": 1,
        "start": date,
        "rotation_start": date,
        "duration": timezone.timedelta(seconds=10800),
        "frequency": CustomOnCallShift.FREQUENCY_HOURLY,
        "interval": 2,
        "until": until,
    }

    on_call_shift = make_on_call_shift(
        organization=organization, shift_type=CustomOnCallShift.TYPE_ROLLING_USERS_EVENT, **data
    )
    rolling_users = [[user_1], [user_2]]
    on_call_shift.add_rolling_users(rolling_users)

    ical_data = on_call_shift.convert_to_ical()
    ical_rrule_until = on_call_shift.until.strftime("%Y%m%dT%H%M%S")
    expected_rrule = f"RRULE:FREQ=HOURLY;UNTIL={ical_rrule_until}Z;INTERVAL=4;WKST=SU"

    assert on_call_shift.event_interval == len(rolling_users) * data["interval"]
    assert expected_rrule in ical_data
