import copy
import itertools
from collections import defaultdict
from decimal import Decimal

from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ImproperlyConfigured
from django.db import models as db_models
from django.db.models import (
    ExpressionWrapper,
    F,
    JSONField,
    OuterRef,
    Q,
    Subquery,
    Value,
)
from django.db.models.expressions import Func
from django.utils.timezone import datetime, timedelta

from .utils2 import plural_days

infinite_defaultdict = lambda: defaultdict(infinite_defaultdict)


import base64

from django.core.files.base import ContentFile

try:
    import libcst
except:
    libcst = None  # XXX


def base64_file(data, name=None):
    if not data:
        return None
    _format, _img_str = data.split(";base64,")
    _name, ext = _format.split("/")
    if not name:
        name = _name.split(":")[-1]
    return ContentFile(base64.b64decode(_img_str), name="{}.{}".format(name, ext))


class NoFieldFoundError(Exception):
    pass


class JSONObject(Func):
    function = "JSON_OBJECT"
    output_field = JSONField()

    def __init__(self, **fields):
        expressions = []
        for key, value in fields.items():
            expressions.extend((Value(key), value))
        super().__init__(*expressions)

    def as_sql(self, compiler, connection, **extra_context):
        """
        if not connection.features.has_json_object_function:
            raise NotSupportedError(
                'JSONObject() is not supported on this database backend.'
            )
        """
        return super().as_sql(compiler, connection, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        return self.as_sql(
            compiler,
            connection,
            function="JSONB_BUILD_OBJECT",
            **extra_context,
        )

    def as_oracle(self, compiler, connection, **extra_context):
        class ArgJoiner:
            def join(self, args):
                args = [" VALUE ".join(arg) for arg in zip(args[::2], args[1::2])]
                return ", ".join(args)

        return self.as_sql(
            compiler,
            connection,
            arg_joiner=ArgJoiner(),
            template="%(function)s(%(expressions)s RETURNING CLOB)",
            **extra_context,
        )


def get_field_from_model(model, field_name):
    try:
        if isinstance(getattr(model, field_name), property):
            return getattr(model, field_name)
        else:
            return [f for f in model._meta.fields if f.name == field_name][0]
    except IndexError:
        try:
            first_rel = [
                v
                for k, v in model._meta.fields_map.items()
                if k == f"{model.__name__}_{field_name}+"
            ][0]
        except IndexError:
            raise NoFieldFoundError(
                f'No field named "{field_name}" on model {model.__name__}'
            )
        else:
            first_fk = first_rel.field
            try:
                second_fk = [
                    f
                    for f in first_fk.model._meta.fields
                    if f != first_fk and f.is_relation
                ][0]
            except IndexError:
                raise NotImplementedError(
                    f'Not a proper implementation for m2m (for field "{model.__name__}.{field_name})"'
                )
            else:
                second_fk.is_m2m = True
                second_fk.initial_related_name = field_name  # TODO?
                # TODO use get_field
                second_fk.original_blank = model._meta.get_field(field_name).blank
                return second_fk


def get_field_from_model_ext(model, field_name):
    if "__" in field_name:
        fk, field_name = field_name.split("__", 1)
        f = model._meta.get_field(fk)
        model = f.related_model
        return get_field_from_model_ext(model, field_name)
    return get_field_from_model(model, field_name)


def level_foreign_key(f, field, model):
    return {
        "k": f.name,
        "type": "LevelForeignKeyField",
        "label": f.verbose_name.capitalize(),
        "required": not f.blank,
        "MAX_LEVEL": f.related_model.MAX_LEVEL,
        "descriptions": {
            l["level"]: l["description"]
            for l in f.related_model.objects.values("level", "description")
        },
        "validators": [],
    }


def from_to(f, field, model):
    field_from = get_field_from_model(model, field["from_field"] + "_from")
    field_from = get_field_from_model(model, field["from_field"] + "_to")
    return {
        "k": field["from_field"],
        "type": "FromToField",
        "label": field["label"],
        "required": not field_from.blank,
        "validators": [
            {"type": "fromTo"},
        ],
    }


# Filters


def plus_days_transformer(filters, prefix, struct):
    plus_k = f"{prefix}__plus"
    value = struct["plus_days"] if filters[plus_k] else 0
    for kk, direction in {"gte": -1, "lte": 1}.items():
        if f"{prefix}__{kk}" in filters:
            filters[f"{prefix}__{kk}"] = filters[f"{prefix}__{kk}"] + timedelta(
                days=value * direction
            )
    del filters[plus_k]


FILTER_TRANSFORMERS = {"plus_days_transformer": plus_days_transformer}


def filter_from_to(f, field, model):
    base_field = field.copy()
    del base_field["via"]
    if not f:
        f = get_field_from_model(model, field["from_field"])
    result = field_from_field(f, base_field, model)
    label_keys = ["from", "to"]
    label_values = ["от", "до"]
    if result["type"] == "DateField":
        label_values = ["с", "по"]
    label_dict = dict(zip(label_keys, label_values))
    qs_dict = {"from": "gte", "to": "lte"}
    fields = [
        {
            "k": field["from_field"] + "_" + kk,
            "qs_k": f"{f.name}__{qs_dict[kk]}",
            "type": result["type"],
            "required": False,
            "label": label_dict[kk],
            "context": result.get("context", {}),
        }
        for kk in ["from", "to"]
    ]
    if (result["type"] == "DateField") and base_field.get("plus_days"):
        fields.append(
            {
                "k": field["from_field"] + "__plus",
                "type": "BooleanField",
                "variant": "CheckButton",
                "required": False,
                "label": f"+{plural_days(base_field['plus_days'])}",
                "context": result.get("context", {}),
            }
        )
    returning = {
        "type": "Fields",
        "fields": fields,
        "constraints": [
            {"type": "from_to", "behaviour": "flip"},
        ],
    }
    if base_field.get("plus_days"):
        returning["transformer"] = "plus_days_transformer"
    return returning


def filter_from_to_month(f, field, model):
    base_field = field.copy()
    del base_field["via"]
    if not f:
        f = get_field_from_model(model, field["from_field"])
    result = {**field_from_field(f, base_field, model), **field}
    return {
        "k": field["from_field"] + "__month",
        "qs_k": f"{f.name}__month",
        "type": "MonthField",
        "required": False,
        "label": result["label"],
        "context": result.get("context", {}),
    }


def filter_multiple_select(f, field, model):
    base_field = field.copy()
    del base_field["via"]
    if not f:
        f = get_field_from_model(model, field["from_field"])
    result = field_from_field(f, base_field, model)
    result["multiple"] = True
    sort_value_by = field.get("sort_value_by")
    if sort_value_by:
        result["sort_value_by"] = sort_value_by
    return {
        "type": "Fields",
        "fields": [result],
    }


def filter_level_foreign_key(f, field, model):
    base_field = field.copy()
    del base_field["via"]
    if not f:
        f = get_field_from_model(model, field["from_field"])

    return {
        "k": f.name,
        "type": "SelectField",
        "label": f.verbose_name.capitalize(),
        "required": False,
        "MAX_LEVEL": f.related_model.MAX_LEVEL,
        "multiple": True,
        "options": [
            {"value": l["level"], "label": l["description"]}
            for l in f.related_model.objects.values("level", "description")
        ],
        "placeholder": "(любой)",
        "validators": [],
    }


def json_master_slave(f, field, model):
    base_field = field.copy()
    del base_field["via"]
    if not f:
        f = get_field_from_model(model, field["from_field"])
    return {
        "k": f.name,
        "type": "DefinedField",
        "simple_defined_field": field.get("simple_defined_field"),
        "label": None,
        "required": False,
        "master_field": field["master_field"],
        "definitions": field["definitions"],
    }


def multiple_choices_select(f, field, model):
    base_field = field.copy()
    del base_field["via"]
    if not f:
        f = get_field_from_model(model, field["from_field"])
    return {
        "k": f.name,
        "type": "SelectField",
        "multiple": True,
        "label": f.verbose_name.capitalize(),
        "required": not f.blank,
        "options": [{"value": k, "label": v} for k, v in f.base_field.choices],
        "is_multiple_choices": True,
    }


field_from_field_transformers = {
    "level_foreign_key": level_foreign_key,
    "from_to": from_to,
    "json_master_slave": json_master_slave,
    "multiple_choices_select": multiple_choices_select,
    # Filters
    "filter_from_to": filter_from_to,
    "filter_from_to_month": filter_from_to_month,
    "filter_multiple_select": filter_multiple_select,
    "filter_level_foreign_key": filter_level_foreign_key,
}


INTEGER_TYPES = {}
for sign_p, sign_v in {
    "": {},
    "Positive": {
        "min": 0,
    },
}.items():
    for size_p, size_v in {
        "": {
            "min": -2147483648,
            "max": 2147483647,
        },
        "Big": {
            # "min": 9223372036854775808, # just formal
            # "max": -9223372036854775807,
        },
        "Small": {"min": -32768, "max": 32767},
    }.items():
        field_type = getattr(db_models, f"{sign_p}{size_p}IntegerField", None)
        if field_type:
            INTEGER_TYPES[field_type] = {**size_v, **sign_v}


def field_from_field(f, field, model):
    via = field.get("via", None)
    if via:
        return field_from_field_transformers[via](f, field, model)
    if isinstance(f, db_models.AutoField):
        return {"k": f.name, "type": "HiddenField", "required": True, "validators": []}
    if isinstance(f, db_models.BooleanField):
        return {
            "k": f.name,
            "type": "BooleanField",
            "label": f.verbose_name.capitalize(),
            "required": False,  # TODO
            "validators": [],
        }
    if isinstance(f, db_models.CharField):
        if f.choices:
            return {
                "k": f.name,
                "type": "SelectField",
                "label": f.verbose_name.capitalize(),
                "required": not f.blank,
                "options": [{"value": k, "label": v} for k, v in f.choices],
                "is_choices": True,
            }
        return {
            "k": f.name,
            "type": "TextField",
            "label": f.verbose_name.capitalize(),
            "required": not f.blank,
            "validators": [
                {"type": "maxLength", "value": f.max_length},
            ],
        }
    if isinstance(f, db_models.TextField):  # TODO refactor with above
        return {
            "k": f.name,
            "type": "TextareaField",
            "label": f.verbose_name.capitalize(),
            "required": not f.blank,
            "validators": [],
        }
    if isinstance(f, db_models.ForeignKey):
        options = None
        optgroup = field.get("optgroup", None)
        params = {}
        if optgroup:
            params = {
                "optgroup": F(optgroup),
                "optgroup_label": field.get(
                    "optgroup_label_expr", F(f"{optgroup}__name")
                ),
            }
        options = list(
            f.related_model.objects.filter(**field.get("filter_expr", {})).values(
                value=F("pk"),
                label=ExpressionWrapper(
                    field.get("label_expr", F("name")),
                    output_field=db_models.CharField(),
                ),
                *field.get("values", []),
                **params,
                **field.get("annotate", {}),
            )
        )
        all_options = options
        dissoc = lambda m, ks: {k: v for k, v in m.items() if k not in ks}
        if optgroup:
            options = []
            key_fn = lambda item: item["optgroup"] or 0
            for k, g in itertools.groupby(sorted(all_options, key=key_fn), key=key_fn):
                items = list(g)
                if not items:
                    continue
                options.append(
                    {
                        "label": items[0]["optgroup_label"],
                        "options": [
                            dissoc(item, ["optgroup", "optgroup_label_expr"])
                            for item in items
                        ],
                    }
                )
        is_m2m = getattr(f, "is_m2m", False)
        create_form = field.get("create_form")
        if create_form and not "related_model" in create_form:  # XXX already processed??
            create_form = read_fields(create_form, f.related_model())  # TODO defaulting
            create_form["verbose_name"] = f.related_model._meta.verbose_name
            create_form["related_model"] = f.related_model
        r = {
            "k": f.initial_related_name if is_m2m else f.name,
            "type": "SelectField",
            "label": f.verbose_name.capitalize(),
            "multiple": is_m2m,
            "is_m2m": is_m2m,
            "required": (not f.original_blank) if is_m2m else (not f.blank),
            "options": options,
            "placeholder": field.get("placeholder", None),
            "validators": [],
            "create_form": create_form,
        }
        return r
    if isinstance(f, db_models.ManyToManyField):
        options = None
        optgroup = field.get("optgroup", None)
        if optgroup:
            option_level_model = f.related_model
            group_level_model = get_field_from_model(
                option_level_model, optgroup
            ).related_model
            options = list(
                group_level_model.objects.annotate(
                    options=Subquery(
                        option_level_model.objects.filter(
                            **{f"{optgroup}__pk": OuterRef("pk")}
                        )
                        .values(f"{optgroup}__pk")
                        .values(s=ArrayAgg(JSONObject(value=F("id"), label=F("name")))),
                        output_field=ArrayField(JSONField()),
                    )
                ).values("options", label=F("name"))
            )
        else:
            options = list(f.related_model.objects.values(value=F("pk"), label=F("name")))
        return {
            "k": f.name,
            "type": "SelectField",
            "label": f.verbose_name.capitalize(),
            "required": not f.blank,
            "options": options,
            "placeholder": field.get("placeholder", None),
            "validators": [],
        }
    integer_type = INTEGER_TYPES.get(type(f))
    if integer_type:
        validators = []

        def get_boundary_validator(boundary):
            for validator in f.validators:
                if (
                    validator.__class__.__name__
                    == f"{boundary.capitalize()}ValueValidator"
                ):
                    return validator.limit_value

        for boundary in ["min", "max"]:
            boundary_value = None
            boundary_validator = get_boundary_validator(boundary)
            if boundary in field:
                boundary_value = field[boundary]
            elif boundary_validator is not None:
                boundary_value = boundary_validator
            # TODO required?
            elif boundary in integer_type:
                boundary_value = integer_type[boundary]
            if boundary_value is not None:
                validators.append({"type": f"{boundary}Number", "value": boundary_value})
        return {
            "k": f.name,
            "type": "NumberField",
            "label": f.verbose_name.capitalize(),
            "required": not f.blank,
            "validators": validators,
            "default": f.default,
        }
    if (
        isinstance(f, ArrayField)
        and isinstance(f.base_field, db_models.CharField)
        and not getattr(f.base_field, "choices", None)
    ):
        validators = []
        return {
            "k": f.name,
            "type": "TextareaField",
            "subtype": "Array",
            "label": f.verbose_name.capitalize(),
            "required": not f.blank,
            "validators": validators,
        }
    # if (
    #    isinstance(f, ArrayField)
    #    and isinstance(f.base_field, db_models.CharField)
    #    and getattr(f.base_field, "choices", None)
    # ):
    #    validators = []
    #    return {
    #        "k": f.name,
    #        "type": "MultipleChoiceField",
    #        "label": f.verbose_name.capitalize(),
    #        "required": not f.blank,
    #        "validators": validators,
    #        "choices": "\n".join([k for k, v in f.base_field.choices]),
    #        "columns": field.get("columns", 1),
    #    }
    if isinstance(f, db_models.ImageField):
        return {
            "k": f.name,
            "type": "Image1Field",
            "label": f.verbose_name.capitalize(),
            "required": not f.blank,
            "upload_to": f.upload_to,
            "validators": [],
        }
    if isinstance(f, db_models.DateField):
        return {
            "k": f.name,
            "type": "DateField",
            "label": f.verbose_name.capitalize(),
            "required": not f.blank,
            "validators": [],
        }
    if isinstance(f, db_models.DecimalField):
        validators = []
        for boundary in ["min", "max"]:
            boundary_value = None
            if boundary in field:
                boundary_value = field[boundary]
            elif hasattr(f, boundary):
                boundary_value = getattr(f, boundary)
            if boundary_value is not None:
                validators.append({"type": f"{boundary}Number", "value": boundary_value})
        return {
            "k": f.name,
            "type": "DecimalField",
            "label": f.verbose_name.capitalize(),
            "required": not f.blank,
            "validators": validators,
        }


def apply_from_field(field, model):
    from_field = field.get("from_field", None)
    if from_field:
        if "." in from_field:  # "Foreign key hierarchy (not a single ForeignKey)"
            current_model, new_model = from_field.split(".", 1)
            return apply_from_field(
                {"original_from_field": from_field, **field, "from_field": new_model},
                getattr(model, current_model).field.related_model,
            )
        try:
            model_field = get_field_from_model(model, from_field)
        except NoFieldFoundError:
            if "via" not in field:
                raise ImproperlyConfigured(f'No field "{from_field}" on model "{model}"')
                del field["from_field"]
            model_field = None
        result = field_from_field(model_field, field, model)
        result.update({k: v for k, v in field.items() if k not in ["create_form"]})
        field = result
        if from_field == "label":
            print("IMP", field.get("impositions"))
    return field


model_redefiners = [
    "ListField",
    "ForeignKeyListField",
    "ForeignKeyUniqueItem",
    "FilterOfRelated",
]


def walk_with_model(struct, func, model):
    fields = struct.get("fields", None)
    if fields:
        if struct.get("type", None) == "ListField":
            model = model["model"]
        elif struct.get("type", None) in model_redefiners:
            model = model._meta.fields_map[struct["k"]].related_model
        struct["fields"] = [walk_with_model(f, func, model) for f in fields]
    return func(struct, model)


def apply_model_to_fields(fields, model):
    return walk_with_model(fields, apply_from_field, model)


def find_option(options, value):
    for option in options:
        if option["value"] == value:
            return option


def find_options(options, values):
    def walk(options):
        result = []
        for option in options:
            if option.get("options"):
                option = {**option, "options": walk(option["options"])}
                if len(option["options"]):
                    result.append(option)
            elif option["value"] in values:
                result.append(option)
        return result

    return walk(options)


def plain_options(v):
    if v["options"] and "options" in v["options"][0]:
        result = []
        for o1 in v["options"]:
            result.extend(o1["options"])
        return result
    else:
        return v["options"]


read_k_fields = None


def read_field(obj, v, getter=getattr, raw=False):
    original_from_field = v.get("original_from_field")
    if original_from_field and "." in original_from_field:
        current_model, original_from_field = original_from_field.split(".", 1)
        print("try to get", obj.__dict__, current_model)
        new_obj = getattr(obj, current_model, None)
        if not new_obj:
            return None
        return read_field(
            new_obj, {**v, "original_from_field": original_from_field}, getter, raw
        )
    json_collection_k = v.get("json_collection")
    if json_collection_k:
        vv = {**v}
        del vv["json_collection"]
        obj2 = getattr(obj, json_collection_k, None) or {}
        return read_field(obj2, vv, getter=lambda o, k: o.get(k, None), raw=True)
    if v["type"] == "SelectField":  # For now foreign key only
        if raw and v.get("multiple"):
            return find_options(
                plain_options(v),
                [int(x) for x in (getter(obj, v["k"]) or "").split(",") if x],
            )
        if v.get("is_choices"):
            id_ = getter(obj, v["k"])
            if id_ is None:
                return None
            try:
                return {"value": id_, "label": getattr(obj, f'get_{v["k"]}_display')()}
            except:
                return find_option(v["options"], id_)
        elif v.get("is_multiple_choices"):
            return find_options(v["options"], getter(obj, v["k"]))
        elif not v.get("is_m2m"):
            id_ = getter(obj, v["k"] + "_id")
            if id_ is None:
                return None
            value_obj = getter(obj, v["k"])
            if not value_obj:
                return None
            try:
                obj_value = (
                    value_obj.__class__.objects.filter(pk=value_obj.pk)
                    .values(
                        label_a23r238r23r8=ExpressionWrapper(
                            v.get("label_expr", F("name")),
                            output_field=db_models.CharField(),
                        ),
                        *v.get("values", []),
                        **v.get("annotate", {}),
                    )
                    .first()
                )
                label = obj_value["label_a23r238r23r8"]
                del obj_value["label_a23r238r23r8"]
            except value_obj.__class__.DoesNotExist:
                return None
            else:
                return {
                    "value": id_,
                    "label": label,
                    **obj_value,
                }
        else:
            if not obj.pk:
                return []
            return find_options(
                v["options"], getter(obj, v["k"]).all().values_list("pk", flat=True)
            )
    # elif v["type"] == "MultipleChoiceField":
    #    return {"selected": getter(obj, v["k"]) or []}
    elif v["type"] == "AttachmentsField":
        if not obj.pk:
            return {"existing": []}
        return {
            "existing": list(
                getter(obj, v["k"])
                .all()
                .values(
                    "id",
                    "document",
                    document_name_72dh923hd=F(v.get("document_name_expr", "name")),
                )
            ),
        }
    elif v["type"] == "LevelForeignKeyField":
        return {
            "level": getter(obj, v["k"] + "_id"),
            "notes": getter(obj, v["k"] + "_notes"),
        }
    elif v["type"] == "BooleanField":
        return getter(obj, v["k"]) or False
    elif v["type"] == "TextField":
        return getter(obj, v["k"]) or ""
    elif v["type"] == "TextareaField" and v.get("subtype", None) != "Array":
        return getter(obj, v["k"]) or ""
    elif v["type"] == "TextareaField" and v.get("subtype", None) == "Array":
        return "\n".join((getter(obj, v["k"]) or []))
    elif v["type"] == "FromToField":
        return {
            "from": getter(obj, v["k"] + "_from"),
            "to": getter(obj, v["k"] + "_to"),
        }
    elif v["type"] == "DecimalField":
        return str(getter(obj, v["k"]))
    elif v["type"] == "Image2Field":
        file = getter(obj, v["k"])
        if type(file) == str:
            return file
        return file.name if file and file.name else None
    elif v["type"] == "Image1Field":
        file = getter(obj, v["k"])
        return file.name if file else None
    elif v["type"] == "ImageField":
        return {"data": getter(obj, v["k"]).name}
    elif v["type"] == "DateField":
        return (
            getter(obj, v["k"])
            if raw
            else (
                getter(obj, v["k"]).strftime("%Y-%m-%d") if getter(obj, v["k"]) else None
            )
        )
    elif v["type"] == "DefinedField" and not v.get("simple_defined_field"):
        try:
            current = v["definitions"][getattr(obj, v["master_field"]).pk]
        except:
            pass
        else:
            return read_k_fields(obj, current)
    else:
        return getter(obj, v["k"])


def read_k_fields(obj, fields):
    data = {}

    def walk1(struct, data, obj):
        k = struct.get("k", None)
        if struct.get("type", []) == "ListField":
            data["items"] = []
            the_items = obj["items"]
            if struct.get("criteria", {}):
                try:
                    the_items = the_items.filter(**struct.get("criteria", {}))
                except:
                    # in case it's not a Queryset, e.g. just a list
                    raise Exception("ListField Criteria application error")
            for i, child in enumerate(list(the_items)):
                data["items"].append({})
                # print("will call with", child, type(child))
                walk1(
                    {k: v for k, v in {**struct, "type": "Fields"}.items() if k != "k"},
                    data["items"][i],
                    child,
                )
        elif struct.get("type", []) == "ForeignKeyListField":
            if not obj.pk:
                return []
            try:
                data[k] = []
            except:
                pass
            related_attr = obj.__class__._meta.fields_map[k].related_name or f"{k}_set"
            for i, child in enumerate(getattr(obj, related_attr).all()):
                data[k].append({})
                # print("will call with", child, type(child))
                walk1(
                    {k: v for k, v in {**struct, "type": "Fields"}.items() if k != "k"},
                    data[k][i],
                    child,
                )
        elif k:
            data[k] = read_field(obj, struct)
        else:
            for f in struct.get("fields", []):
                walk1(f, data, obj)

    walk1(fields, data, obj)

    return data["items"] if fields["type"] == "ListField" else data


def read_fields(fields, obj):
    fields = walk_with_model(
        fields, apply_from_field, obj if type(obj) == dict else obj.__class__
    )
    return {
        "fields": fields,
        "data": read_k_fields(obj, fields),
    }


def gather_labels(fields):
    result = []

    def walk(field):
        if "k" in field:
            result.append(field["label"])
        elif "fields" in field:
            for f in field["fields"]:
                walk(f)

    walk(fields)
    return result


def hide_from_field(definition):
    def walk(node):
        f = {**node}
        if "from_field" in f:
            del f["from_field"]
        if f.get("fields"):
            f["fields"] = [walk(c) for c in f["fields"]]
        return f

    return walk(definition)


def get_fields_for_fields_options_field(fields, model):
    fields = walk_with_model(fields, apply_from_field, model)
    result = []
    required_by_default = []

    def walk(field):
        if "position_k" in field:
            result.append(
                {
                    "value": field["position_k"],
                    "labels": gather_labels(field),
                }
            )
        elif "k" in field:
            result.append(
                {
                    "value": field["k"],
                    "label": field["label"],
                    "required_by_default": field["required"],
                }
            )
            if field["required"]:
                required_by_default.append(field["k"])
        elif "fields" in field:
            for f in field["fields"]:
                walk(f)

    walk(fields)
    return hide_from_field(fields), result, required_by_default


def validate_fields(fields, model, data):
    pass


def get_k_fields(fields):
    def walk1(struct, func, path=None):
        if not path:
            path = []
        k = struct.get("k", None)
        if k:
            path = [*path, k]
        for f in struct.get("fields", []):
            walk1(f, func, path)
        if k:
            func(struct, path)

    def assign_by_path(d, path, value):
        p = r = d
        rk = None
        for k in path:
            p = r
            rk = k
            r = r[k]
        if (rk not in p) or not p[rk].keys():
            p[rk] = value
        if (rk in p) and value.get("type", None) == "ListField":
            value = copy.deepcopy(value)
            del value["fields"]
            p[rk]["_field"] = value
        if (rk in p) and value.get("type", None) == "ForeignKeyListField":
            value = copy.deepcopy(value)
            del value["fields"]
            p[rk]["_field"] = value
        return r

    k_fields = infinite_defaultdict()

    def walk1_func(struct, path):
        if not path:
            return
        return assign_by_path(k_fields, path, struct)

    walk1(fields, walk1_func)
    return k_fields


def read_field_into_qs(obj, v):
    getter = lambda obj, k, default=None: obj.get(k, default) if obj else None
    qs_k = v.get("qs_k", v["k"])
    if v["type"] == "SelectField":  # For now foreign key only
        if v["multiple"]:
            value = [int(x) for x in (getter(obj, v["k"]) or "").split(",") if x]
            if value:
                return {f"{qs_k}__in": value}
        else:
            raise NotImplementedError()
    elif v["type"] == "DateField":
        value = getter(obj, v["k"])
        if value:
            value = datetime.strptime(value, "%Y-%m-%d").date()
            return {
                qs_k: value,
            }
    elif v["type"] == "BooleanField":
        value = getter(obj, v["k"])
        value = value == "yes"
        return {
            qs_k: value,
        }
    else:
        print(f"No read_field_into_qs implementation for field {v['k']}")
        return {}
    return {}


def walk_the_tree(tree, f, parents=None):
    if not parents:
        parents = []
    fields = tree.get("fields")
    tree = {k: v for k, v in tree.items()}
    if fields:
        tree["fields"] = [walk_the_tree(field, f, [*parents, tree]) for field in fields]
    return f(tree, parents)


def read_filter_fields(fields, GET, model):
    fields = walk_with_model(fields, apply_from_field, model)
    # print(json.dumps(fields, default=repr, ensure_ascii=False))
    def make_not_required(field, _):
        if field.get("required"):
            print(field, " is required")
            field["required"] = False
        return field

    fields = walk_the_tree(fields, make_not_required)
    data = {}
    # data, filter_expr
    filters = {}

    def walk1(struct, data, obj, k_path=None):
        if not k_path:
            k_path = []
        k = struct.get("k", None)
        fields = struct.get("fields", [])
        if fields:
            if k:
                data[k] = {}
                data = data[k]
                k_path = [*k_path, k]
            for f in fields:
                walk1(f, data, obj, k_path=k_path)
            transformer = struct.get("transformer")
            if transformer:
                FILTER_TRANSFORMERS[transformer](
                    filters, "__".join([*k_path, struct["from_field"]]), struct
                )
        elif k:
            data[k] = read_field(
                obj,
                struct,
                getter=lambda obj, k, default=None: obj.get(k, default) if obj else None,
                raw=True,
            )
            filters.update(
                {
                    "__".join([*k_path, k]): v
                    for k, v in read_field_into_qs(obj, struct).items()
                }
            )

    walk1(fields, data, GET)

    return {
        "fields": fields,
        "data": data,
    }, filters


def do_write_fields(fields, obj, data, files=None):
    fields = walk_with_model(
        fields, apply_from_field, obj if type(obj) == dict else obj.__class__
    )
    k_fields = get_k_fields(fields)

    def get_by_path(struct, path):
        r = struct
        for k in path:
            try:
                r = r[k]
            except (IndexError, KeyError):
                return None
        return r

    def set_by_path(struct, path, value):
        r = struct
        for k in path[:-1]:
            try:
                r = r[k]
            except (IndexError, KeyError):
                return None
        r[path[-1]] = value

    # print(json.dumps(fields, indent=4, ensure_ascii=False, default=repr))
    # print(json.dumps(k_fields, indent=4, ensure_ascii=False, default=repr))

    def assign_field(obj, v, path2=None, setter=setattr, raw=False):
        if "." in (v.get("original_from_field") or ""):
            return  # noop
        json_collection_k = v.get("json_collection")
        if json_collection_k:
            if not getattr(obj, json_collection_k, None):
                setattr(obj, json_collection_k, {})
                obj.save()
        if isinstance(v, defaultdict):
            return  # XXX fix
        if json_collection_k:
            del v["json_collection"]
            if not getattr(obj, json_collection_k, None):
                setattr(obj, json_collection_k, {})
            obj2 = getattr(obj, json_collection_k, None)
            assign_field(
                obj2, v, path2, setter=lambda o, k, v: o.__setitem__(k, v), raw=True
            )
            return
        try:
            parent_val = get_by_path(data, path2[:-1])
        except:
            parent_val = None
        val = get_by_path(data, path2)
        if v["type"] == "SelectField":  # For now foreign key only
            # print('SelectField', v)
            if v.get("is_choices"):
                setter(
                    obj,
                    v["k"],
                    (val if type(val) == str else val.get("value", None))
                    if val
                    else None,
                )
            elif v.get("is_multiple_choices"):
                setter(
                    obj,
                    v["k"],
                    [o["value"] for o in val] if val else [],
                )
            elif not v.get("is_m2m"):
                setter(obj, v["k"] + "_id", val and val.get("value", None))
            else:
                val = val or []
                values = [x["value"] for x in val]
                m2m_related = getattr(obj, v["k"])
                for vv in m2m_related.all():
                    if vv.pk not in values:
                        m2m_related.remove(vv)
                existing = [x.pk for x in m2m_related.all()]
                for vv in val or []:
                    if vv["value"] not in existing:
                        m2m_related.add(m2m_related.model.objects.get(pk=vv["value"]))
        elif v["type"] == "LevelForeignKeyField":
            setter(obj, v["k"] + "_id", val["level"])
            setter(obj, v["k"] + "_notes", val.get("notes", ""))
        elif v["type"] == "BooleanField" or v["type"] == "SwitchField":
            setter(obj, v["k"], val or False)
        # elif v["type"] == "MultipleChoiceField":
        #    setter(obj, v["k"], (val or {}).get("selected") or [])
        elif v["type"] == "TextField":
            setter(obj, v["k"], val or "")
        elif v["type"] == "TextareaField" and v.get("subtype", None) != "Array":
            setter(obj, v["k"], val or "")
        elif v["type"] == "TextareaField" and v.get("subtype", None) == "Array":
            setter(obj, v["k"], (val or "").split("\n"))
        elif v["type"] == "FromToField":
            setter(obj, v["k"] + "_from", int(val.get("from")))
            setter(obj, v["k"] + "_to", int(val.get("to")))
        elif v["type"] == "Image1Field":
            if type(val) == dict:  # change
                uid = val["its_uid_for_file_to_upload_239r8h239rh239r"]
                file = files[uid]
                setter(obj, v["k"], file)
            elif val == None:  # delete
                setter(obj, v["k"], None)
        elif v["type"] == "Image2Field":
            if raw:
                setter(obj, v["k"], val)
            else:
                setter(obj, v["k"], base64_file(val))
        elif v["type"] == "DecimalField":
            setter(obj, v["k"], Decimal(str(val or 0)))
        elif v["type"] == "DateField":
            if raw:
                setter(obj, v["k"], val[:10] if val else None)
            else:
                setter(
                    obj,
                    v["k"],
                    datetime.strptime(val[:10], "%Y-%m-%d") if val else None,
                )
        elif v["type"] == "DefinedField" and not v.get("simple_defined_field"):
            try:
                current = v["definitions"][parent_val[v["master_field"]]["value"]]
            except:
                pass
            else:
                obj.save()
                write_fields(current, obj, val, files)
        else:
            setter(obj, v["k"], val)

    def walk2(items, obj, path=[]):
        for k, v in items.items():
            # if not isinstance(v, dict) or not 'type' in v:
            #    continue
            path2 = [*path, k]
            if (
                "_field" not in v
                and not v.get("is_m2m", False)
                and not v["type"] == "AttachmentsField"
            ):
                assign_field(obj, v, path2)
        # print(obj, obj.__dict__)
        obj.save()

        for k, v in items.items():
            # if not isinstance(v, dict) or not 'type' in v:
            #    continue
            path2 = [*path, k]
            if "_field" not in v and v.get("is_m2m", False):
                assign_field(obj, v, path2)
        """
        """
        for k, v in items.items():
            # if not isinstance(v, dict) or not 'type' in v:
            #    continue
            if v["type"] != "AttachmentsField":
                continue
            m2m_field = obj.__class__._meta.get_field(k)
            value = get_by_path(data, [*path, k])
            if not value:
                value = {}
            value = {"existing": [], "added": [], **value}
            existing_ids = [x["id"] for x in value.get("existing", [])]
            manager = getattr(obj, k)
            for att in manager.all():
                if att.id not in existing_ids:
                    manager.remove(att)
            for added in value.get("added", []):
                uid = added["its_uid_for_file_to_upload_239r8h239rh239r"]
                file = files[uid]
                doc = m2m_field.related_model.objects.create(
                    **{
                        v.get("document_name_expr", "name"): file.name,
                        "document": file,
                    }
                )
                print("doc id", doc.id)
                manager.add(doc)
            # m2m_field.related_model
        # print(obj, obj.__dict__)
        for k, v in items.items():
            # if not isinstance(v, dict) or not 'type' in v:
            #    continue
            if v["type"] == "AttachmentsField":
                continue
            if k == "_field":
                continue
            path2 = [*path, k]
            if "_field" in v:
                fk_field = obj.__class__._meta.fields_map[k].field
                updated_items = get_by_path(data, path2) or []
                existing_items = fk_field.model.objects.filter(**{fk_field.name: obj})
                existing_items.filter(
                    ~Q(
                        pk__in=[
                            x.get("id", None) for x in updated_items if x.get("id", None)
                        ]
                    )
                ).delete()
                for j, x in enumerate(updated_items):
                    id_ = x.get("id", None)
                    print("aaa", id_)
                    if id_:
                        try:
                            child = fk_field.model.objects.get(pk=id_)
                        except fk_field.model.DoesNotExist:
                            continue  # TODO different strategy?
                    else:
                        child = fk_field.model()
                    setattr(child, fk_field.name, obj)
                    if v["_field"].get("ordered"):
                        set_by_path(data, [*path2, j, "order"], j + 1)
                    walk2(v, child, [*path2, j])

    walk2(k_fields, obj)
    return obj


def write_fields(fields, obj, data, files=None):
    """
    For both normal fields and ListField
    """
    if fields["type"] != "ListField":
        return do_write_fields(fields, obj, data, files=files)
    MODEL = obj["model"]
    result = []
    the_fields = {**fields, "type": "Fields"}
    mqs = MODEL.objects.filter(**fields.get("criteria", {}))
    mqs.filter(~Q(id__in=[x["id"] for x in data if "id" in x])).delete()
    objs = {}
    for item in mqs:
        objs[item.id] = item
    for item in data:
        subobj = objs.get(item["id"]) if "id" in item else MODEL()
        if "id" in item:
            for k, v in fields.get("criteria", {}).items():
                current = getattr(subobj, k)
                if current != v:
                    raise Exception(
                        f"ListField Criteria doesn't match: expected {v}, got {current}"
                    )  # TODO enhance
        else:
            for k, v in fields.get("criteria", {}).items():
                setattr(subobj, k, v)
        result.append(do_write_fields(the_fields, subobj, item, files=files))
    return result


def apply_fields_included_and_required(
    definition, fields_included_and_required, required_by_default
):
    newDefinition = copy.deepcopy(definition)
    isIncluded = lambda k: k and (
        k in required_by_default
        or fields_included_and_required.get(k, {}).get("available")
    )
    isRequired = lambda k: k and (
        k in required_by_default
        or fields_included_and_required.get(k, {}).get("required")
    )

    def spreadRequired(node, required):
        if node.get("fields"):
            return {
                **node,
                "fields": [spreadRequired(f, required) for f in node["fields"]],
            }
        else:
            if node:
                node["required"] = required
            return node

    def walk(node):
        k = node.get("k")
        position_k = node.get("position_k")
        fields = node.get("fields")

        if isIncluded(position_k):
            return spreadRequired(node, isRequired(position_k))

        if isIncluded(k) and not fields:
            return spreadRequired(node, isRequired(k))

        if fields:
            fields = [f for f in [walk(f) for f in fields] if f]
            if not fields:
                return None
            return {**node, "fields": fields}

    return walk(newDefinition)
