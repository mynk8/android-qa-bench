"""Deterministic checks for tasks-0012. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'tasks'
PACKAGE = 'org.tasks'
SEED = 'inbox_basic'
DB = 'database'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'complete_first': [{'id': 'org.tasks:id/completeBox'}, {'desc': 'Complete'}, {'desc': 'Mark complete'}], 'fab_new': [{'desc': 'Create new task'}, {'desc': 'New task'}, {'id': 'org.tasks:id/fab'}], 'title_field': [{'id': 'org.tasks:id/title'}, {'text': 'Task name'}, {'text': 'Title'}], 'add_subtask': [{'text': 'Subtasks'}, {'text': 'Add subtask'}, {'desc': 'Add subtask'}], 'subtask_field': [{'text': 'Subtask'}, {'id': 'org.tasks:id/title_subtask'}, {'text': ''}], 'save': [{'desc': 'Save'}, {'text': 'Save'}, {'desc': 'Done'}], 'search': [{'desc': 'Search'}, {'id': 'org.tasks:id/menu_search'}], 'search_field': [{'id': 'org.tasks:id/search_src_text'}, {'text': 'Search'}], 'repeat_row': [{'text': 'Repeats monthly'}, {'text': 'Monthly'}, {'text': 'Every month'}, {'text': 'Does not repeat'}], 'custom': [{'text': 'Custom…'}, {'text': 'Custom...'}, {'text': 'Custom'}], 'ends_spinner': [{'text': 'Never'}, {'text': 'Ends'}, {'id': 'org.tasks:id/repeat_until'}], 'ends_after': [{'text': 'After'}, {'text': 'After N occurrences'}], 'ends_never': [{'text': 'Never'}], 'count_field': [{'id': 'org.tasks:id/repeat_times_value'}, {'text': '1'}], 'dialog_ok': [{'text': 'OK'}, {'text': 'Ok'}, {'text': 'Done'}], 'sort_desc': [{'text': 'Descending'}, {'text': 'Due date, newest first'}], 'group_by': [{'text': 'Sort'}, {'text': 'Group by'}, {'text': 'Grouping'}], 'group_due': [{'text': 'Due date'}, {'text': 'Due'}, {'text': 'By due date'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

def _app_texts(dev):
    """Texts of the app's own windows only (the status-bar clock must not leak in)."""
    out = []
    for n in h.nodes(dev):
        pk = n.get("package")
        if pk and pk != PACKAGE:
            continue
        for k in ("text", "desc"):
            v = n.get(k)
            if v:
                out.append(str(v))
    return out


def _day(days, extra):
    return ("((CAST(strftime('%s','now','start of day','+" + str(days) + " days'," + extra
            + ") AS INTEGER))*1000)")


def _write(dev, stmt):
    dev.write_seed_sql(DB, [stmt])
    dev.launch(PACKAGE)
    dev.wait_idle()


def _chip_extra(dev, title, due_sql, start_sql):
    """Texts that appear in the list when the task gets a start date, all else equal.
    Step 1: due date set, no start date. Step 2: start date set. The head hides the start
    chip when start == due; the buggy build shows it (start != start-of-day(due))."""
    _write(dev, "UPDATE tasks SET dueDate = " + due_sql + ", hideUntil = 0 WHERE title='" + title + "'")
    base = _app_texts(dev)
    _write(dev, "UPDATE tasks SET hideUntil = " + start_sql + " WHERE title='" + title + "'")
    after = _app_texts(dev)
    extra = [t for t in after if t not in base]
    return base, after, extra


def _target(dev, p):
    h.fresh(dev, APP, SEED)
    # Buy milk: due in 5 days at 3:00 PM (seconds > 0 marks a due time); start == due exactly
    base, after, extra = _chip_extra(dev, "Buy milk", _day(5, "'+15 hours','+1 seconds'"), "dueDate")
    return h.has(dev, "Buy milk") and not extra, {"extra_texts": extra, "after": after[:50]}


def _held(dev, p):
    h.fresh(dev, APP, SEED)
    # Pay rent: date-only due (noon, no seconds) in 20 days; start == due exactly
    base, after, extra = _chip_extra(dev, "Pay rent", _day(20, "'+12 hours'"), "dueDate")
    return h.has(dev, "Pay rent") and not extra, {"extra_texts": extra, "after": after[:50]}


def _keep(dev, p):
    h.fresh(dev, APP, SEED)
    # start a day before the due time: the start chip must still show on both builds
    base, after, extra = _chip_extra(dev, "Buy milk", _day(5, "'+15 hours','+1 seconds'"), "dueDate - 86400000")
    return h.has(dev, "Buy milk") and len(extra) > 0, {"extra_texts": extra, "after": after[:50]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
