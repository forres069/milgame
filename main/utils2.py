from collections import defaultdict
from functools import reduce

infinite_defaultdict = lambda: defaultdict(infinite_defaultdict)


def plural_days(n):
    return str(n) + " day(s)"


def unique(a):
    r = []
    for x in a:
        if x not in r:
            r.append(x)
    return r


def dissoc(d, *keys):
    return {k: v for k, v in d.items() if k not in keys}


def menu_view(k):
    def menu_view_decorator(cls):
        menu_views[k].append(cls)
        return cls

    return menu_view_decorator


def all_subclasses(cls):
    for c in cls.__subclasses__():
        for s in all_subclasses(c):
            yield s
        yield c


def validation_error_message(e):
    if hasattr(e, "message"):
        if e.params:
            return e.message % e.params
        else:
            return e.message
    if hasattr(e, "error_list"):
        return validation_error_message(e.error_list[0])
    raise NotImplemented


default_merge_fn = lambda d1, d2: {
    **d1,
    **{k: v for k, v in d2.items() if not (k in d1 and v is None)},
}


def recursive_merge_dict(*dicts, merge_fn=default_merge_fn):
    """
    In [8]: import minerva.utils2

    In [17]: reload(minerva.utils2); minerva.utils2.recursive_merge_dict({"b": {}}, {"a": 1})
    Out[17]: {'b': {}, 'a': 1}

    In [18]: reload(minerva.utils2); minerva.utils2.recursive_merge_dict({"b": {}}, {"b": 1})
    Out[18]: {'b': 1}

    In [19]: reload(minerva.utils2); minerva.utils2.recursive_merge_dict({"b": {}}, {"b": {"bb": 0}})
    Out[19]: {'b': {'bb': 0}}

    In [20]: reload(minerva.utils2); minerva.utils2.recursive_merge_dict({"b": {"c": "aaa"}}, {"b": {"bb": 0}})
    Out[20]: {'b': {'c': 'aaa', 'bb': 0}}

    In [21]: reload(minerva.utils2); minerva.utils2.recursive_merge_dict(None, {"b": {"c": "aaa"}}, {"b": {"bb": 0}})
    Out[21]: {'b': {'c': 'aaa', 'bb': 0}}

    In [24]: reload(minerva.utils2); minerva.utils2.recursive_merge_dict({"a": 1}, {"a": None})
    Out[24]: {'a': 1}
    """

    def inner_fn(d1, d2):
        if not d1:
            d1 = {}
        if not d2:
            d2 = {}
        # avoid "shadowing" by "None" values from d2
        # e.g. {"a": 1}, {"a": None} -> {"a": 1}
        result = default_merge_fn(d1, d2)
        dict_or_None = lambda x: x is None or isinstance(x, dict)
        for k in set([*d1.keys(), *d2.keys()]):
            # if at lease one is dict, while other one is dict_or_None
            a = d1.get(k)
            b = d2.get(k)
            if (isinstance(a, dict) and dict_or_None(b)) or (
                isinstance(b, dict) and dict_or_None(a)
            ):
                result[k] = inner_fn(a, b)
        return result

    return reduce(inner_fn, dicts, {})
