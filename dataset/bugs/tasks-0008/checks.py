"""Deterministic checks for tasks-0008. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'tasks'
PACKAGE = 'org.tasks'
SEED = 'inbox_basic'
DB = 'database'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'complete_first': [{'id': 'org.tasks:id/completeBox'}, {'desc': 'Complete'}, {'desc': 'Mark complete'}], 'fab_new': [{'desc': 'Create new task'}, {'desc': 'New task'}, {'id': 'org.tasks:id/fab'}], 'title_field': [{'id': 'org.tasks:id/title'}, {'text': 'Task name'}, {'text': 'Title'}], 'add_subtask': [{'text': 'Subtasks'}, {'text': 'Add subtask'}, {'desc': 'Add subtask'}], 'subtask_field': [{'text': 'Subtask'}, {'id': 'org.tasks:id/title_subtask'}, {'text': ''}], 'save': [{'desc': 'Save'}, {'text': 'Save'}, {'desc': 'Done'}], 'search': [{'desc': 'Search'}, {'id': 'org.tasks:id/menu_search'}], 'search_field': [{'id': 'org.tasks:id/search_src_text'}, {'text': 'Search'}], 'repeat_row': [{'text': 'Repeats monthly'}, {'text': 'Monthly'}, {'text': 'Every month'}, {'text': 'Does not repeat'}], 'custom': [{'text': 'Custom…'}, {'text': 'Custom...'}, {'text': 'Custom'}], 'ends_spinner': [{'text': 'Never'}, {'text': 'Ends'}, {'id': 'org.tasks:id/repeat_until'}], 'ends_after': [{'text': 'After'}, {'text': 'After N occurrences'}], 'ends_never': [{'text': 'Never'}], 'count_field': [{'id': 'org.tasks:id/repeat_times_value'}, {'text': '1'}], 'dialog_ok': [{'text': 'OK'}, {'text': 'Ok'}, {'text': 'Done'}], 'overflow': [{'desc': 'More options'}, {'desc': 'More'}, {'id': 'org.tasks:id/menu_overflow'}], 'group_by': [{'text': 'Sort'}, {'text': 'Group by'}, {'text': 'Grouping'}, {'text': 'Group'}, {'desc': 'Group'}], 'group_due': [{'text': 'Due date'}, {'text': 'Due'}, {'text': 'By due date'}], 'sort_order': [{'text': 'Sort'}, {'text': 'Sort by'}], 'sort_desc': [{'text': 'Descending'}, {'text': 'Due date, newest first'}, {'text': 'Z to A'}], 'sort_icon': [{'desc': 'Sort'}, {'text': 'Sort'}], 'group_toggle': [{'text': 'Ascending'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p


def _apply(dev, p):
    """Open the Sort sheet and flip the grouping order. At head the default grouping is
    already 'By due date' (ascending), and the Grouping row's order button is the first
    'Ascending' on the sheet, so one tap makes it Descending. Back closes the sheet."""
    h.go(dev, p, "sort_icon")
    h.go(dev, p, "group_toggle")
    dev.back()
    dev.wait_idle()


def _headers_between(ts, first, second):
    i, j = h.index_of(ts, first), h.index_of(ts, second)
    if i < 0 or j < 0 or j <= i:
        return None, i, j
    return [t for t in ts[i + 1:j] if t.strip().startswith("Due ")], i, j


def _target(dev, p):
    h.fresh(dev, APP, SEED)
    _apply(dev, p)
    ts = h.texts(dev)
    hdrs, i, j = _headers_between(ts, "Read docs", "Pay rent")
    # descending: Read docs (no date) first, then Pay rent, which needs its own "Due ..." header
    return bool(hdrs), {"read_docs": i, "pay_rent": j, "headers_between": hdrs, "texts": ts[:60]}


def _held(dev, p):
    h.fresh(dev, APP, SEED)
    dev.write_seed_sql("database", [
        "INSERT INTO tasks (title, dueDate, hideUntil, notes, recurrence, parent, completed, deleted, created, modified, importance, `order`, remoteId, `estimatedSeconds`, `elapsedSeconds`, `timerStart`, `notificationFlags`, `lastNotified`, `collapsed`) VALUES ('Water plants', ((CAST(strftime('%s','now','start of day','+30 days','+12 hours') AS INTEGER))*1000), 0, '', '', 0, 0, 0, 0, 0, 3, 7, 'seed-7', 0, 0, 0, 0, 0, 0);"
    ])
    dev.launch(PACKAGE)
    dev.wait_idle()
    _apply(dev, p)
    ts = h.texts(dev)
    hdrs, i, j = _headers_between(ts, "Read docs", "Water plants")
    return bool(hdrs), {"read_docs": i, "water_plants": j, "headers_between": hdrs, "texts": ts[:60]}


def _keep(dev, p):
    h.fresh(dev, APP, SEED)
    return h.has(dev, "Buy milk") and h.has(dev, "Read docs"), {"texts": h.texts(dev)[:40]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
