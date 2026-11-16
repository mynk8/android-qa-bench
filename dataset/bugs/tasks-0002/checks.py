"""Deterministic checks for tasks-0002. passed=True means intended behaviour (bug absent).
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

def _order(dev):
    ts = h.texts(dev); a, b = h.index_of(ts, "Charge phone"), h.index_of(ts, "Print tickets")
    return a >= 0 and b >= 0 and a < b, {"charge": a, "print": b}
def _target(dev, p):
    h.fresh(dev, APP, SEED); return _order(dev)
def _held(dev, p):
    h.fresh(dev, APP, SEED); h.relaunch(dev, PACKAGE); return _order(dev)
def _keep(dev, p):
    h.fresh(dev, APP, SEED); return h.has(dev, "Pack for trip") and h.has(dev, "Buy milk"), {"texts": h.texts(dev)[:30]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
