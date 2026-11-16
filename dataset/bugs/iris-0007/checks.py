"""Deterministic checks for iris-0007. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'iris'
PACKAGE = 'com.iris.gallery'
SEED = 'album_basic'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'album': [{'text': 'IrisSeed'}, {'desc': 'IrisSeed'}], 'open_big': [{'desc': 'big.jpg'}, {'text': 'big.jpg'}], 'open_huge': [{'desc': 'huge.jpg'}, {'text': 'huge.jpg'}], 'details': [{'desc': 'Details'}, {'desc': 'Info'}, {'text': 'Details'}, {'desc': 'More options'}], 'details_item': [{'text': 'Details'}, {'text': 'Info'}], 'rename': [{'text': 'Rename'}, {'desc': 'Rename'}], 'title_field': [{'text': 'Title'}, {'text': 'Sunset'}], 'ok': [{'text': 'OK'}, {'text': 'Save'}], 'new_album': [{'text': 'New album'}, {'text': 'Create new album'}, {'text': 'Create'}], 'move': [{'text': 'Move to album'}, {'text': 'Move to Album'}, {'desc': 'Move'}], 'album_name': [{'text': 'Album name'}, {'text': 'Name'}], 'albums_tab': [{'text': 'Albums'}, {'desc': 'Albums'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

def _open_album(dev, p, which):
    """Open the IrisSeed album from the Albums tab; if the photo is still not listed (the app
    may have queried MediaStore before the seed scan finished) relaunch and try again."""
    for _ in range(3):
        if h.find(dev, p["nav"][which]) is not None:
            return
        h.go_opt(dev, p, "albums_tab")
        h.go_opt(dev, p, "album")
        if h.find(dev, p["nav"][which]) is not None:
            return
        h.relaunch(dev, PACKAGE)

def _details(dev, p, which):
    h.fresh(dev, APP, SEED)
    _open_album(dev, p, which)
    h.go(dev, p, which)
    h.go(dev, p, "details")
    h.go_opt(dev, p, "details_item")
    return h.texts(dev)

def _target(dev, p):
    ts = _details(dev, p, "open_big")
    return any("1.5 MB" in t for t in ts) and not any("1.4 MB" in t for t in ts), {"texts": ts[:40]}

def _held(dev, p):
    ts = _details(dev, p, "open_huge")
    return any("2.5 MB" in t for t in ts) and not any("2.4 MB" in t for t in ts), {"texts": ts[:40]}

def _keep(dev, p):
    ts = _details(dev, p, "open_big")
    return any("big.jpg" in t for t in ts), {"texts": ts[:40]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
