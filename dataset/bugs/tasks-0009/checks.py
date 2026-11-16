"""Deterministic checks for tasks-0009. passed=True means intended behaviour (bug absent).
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

def _search(dev, p, term):
    """Open Search, type the term and SUBMIT it (Enter / search key). Submitting turns the
    search into a SearchFilter and collapses the search field; only then is the list-fragment
    back callback (removed by the bug) the one that has to restore the full list. A typed-only
    search is collapsed by the Compose BackHandler on both builds."""
    h.fresh(dev, APP, SEED)
    h.go(dev, p, "search")
    h.type_into(dev, p, "search_field", term)
    h.key(dev, "ENTER")
    if h.find(dev, [{"id": "org.tasks:id/search_src_text"}]) is not None and not h.has(dev, "Matching"):
        raise h.StepMissing("search not submitted (Enter did not reach the SearchView)")


def _back_out(dev):
    # clean head: back restores the full list; buggy head: back finishes the activity.
    # Submitting hides the keyboard (MainActivity hides it on a filter change), so one press.
    dev.back()
    dev.wait_idle()


def _target(dev, p):
    _search(dev, p, "milk")
    _back_out(dev)
    return h.has(dev, "Pay rent"), {"texts": h.texts(dev)[:40]}


def _held(dev, p):
    _search(dev, p, "rent")
    _back_out(dev)
    return h.has(dev, "Read docs") and h.has(dev, "Buy milk"), {"texts": h.texts(dev)[:40]}


def _keep(dev, p):
    _search(dev, p, "milk")
    return h.has(dev, "Buy milk") and not h.has(dev, "Pay rent"), {"texts": h.texts(dev)[:40]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
