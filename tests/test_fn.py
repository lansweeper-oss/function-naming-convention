# ruff: noqa: E501
import dataclasses
import unittest
from unittest import mock

import grpc
from crossplane.function import logging, resource
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from google.protobuf import duration_pb2 as durationpb
from google.protobuf import json_format
from google.protobuf import struct_pb2 as structpb

import function.constants as c
from function import fn


@dataclasses.dataclass
class TestCase:
    reason: str
    req: fnv1.RunFunctionRequest
    want: fnv1.RunFunctionResponse


CONTEXT = structpb.Struct(
    fields={
        c.CONTEXT_KEY_ENVIRONMENT: structpb.Value(
            struct_value=structpb.Struct(
                fields={
                    "account": structpb.Value(string_value="test"),
                    "accountCode": structpb.Value(string_value="tst"),
                    "accountId": structpb.Value(string_value="123456789012"),
                    "awsTags": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                "environment": structpb.Value(string_value="Development"),
                                "owner": structpb.Value(string_value="Team A"),
                            }
                        )
                    ),
                    "namePrefix": structpb.Value(string_value="aa-tst-usw2"),
                    "region": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                "region": structpb.Value(string_value="us-west-2"),
                                "regionCode": structpb.Value(string_value="usw2"),
                            }
                        )
                    ),
                }
            )
        )
    }
)
PREFIX = f"{c.ANNOTATION_PREFIX}{c.DEFAULT_PREFIX_SEPARATOR}"
TESTCASES = [
    TestCase(
        reason="The function should be able to reference a context sub map.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {
                                        "do-not-delete": "me",
                                        f"{PREFIX}account": "bar",
                                        f"{PREFIX}ls-domain": "core",
                                    },
                                    "name": "foo",
                                },
                                "spec": {},
                            }
                        )
                    ),
                }
            ),
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_CONTEXT: structpb.Value(
                                    string_value=f"{c.CONTEXT_KEY_ENVIRONMENT}/region"
                                ),
                                c.INPUT_ENV_TO_LABEL: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={
                                            "region": structpb.Value(string_value="regionName"),
                                            "regionCode": structpb.Value(string_value="regionCode"),
                                        }
                                    )
                                ),
                                c.INPUT_LABELS: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={c.INPUT_PREFIX: structpb.Value(string_value="bb")}
                                    )
                                ),
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="region-code"),
                                            structpb.Value(string_value="ls-domain"),
                                        ]
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {
                                        "do-not-delete": "me",
                                    },
                                    "name": "usw2-core-foo",
                                    "labels": {
                                        "bb/region": "us-west-2",
                                        "bb/region-code": "usw2",
                                    },
                                },
                                "spec": {},
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="The function should modify the metadata of the resource.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {
                                        "do-not-delete": "me",
                                        f"{PREFIX}account": "bar",
                                        f"{PREFIX}ls-domain": "core",
                                    },
                                    "name": "foo",
                                },
                                "spec": {},
                            }
                        )
                    ),
                }
            ),
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_ENV_TO_LABEL: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={
                                            "account": structpb.Value(string_value="account"),
                                            "accountCode": structpb.Value(
                                                string_value="accountCode"
                                            ),
                                            "accountId": structpb.Value(string_value="accountId"),
                                            "namePrefix": structpb.Value(string_value="namePrefix"),
                                            "region.region": structpb.Value(
                                                string_value="regionName"
                                            ),
                                            "region.regionCode": structpb.Value(
                                                string_value="regionCode"
                                            ),
                                        }
                                    )
                                ),
                                c.INPUT_LABELS: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={c.INPUT_PREFIX: structpb.Value(string_value="bb")}
                                    )
                                ),
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="name-prefix"),
                                            structpb.Value(string_value="ls-domain"),
                                        ]
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {
                                        "do-not-delete": "me",
                                    },
                                    "name": "aa-tst-usw2-core-foo",
                                    "labels": {
                                        "bb/account": "bar",
                                        "bb/account-code": "tst",
                                        "bb/account-id": "123456789012",
                                        "bb/name-prefix": "aa-tst-usw2",
                                        "bb/region": "us-west-2",
                                        "bb/region-code": "usw2",
                                    },
                                },
                                "spec": {},
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="The function should be able to tag resources from a context field.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {
                                        "do-not-delete": "me",
                                        f"{PREFIX}account": "bar",
                                        f"{PREFIX}ls-domain": "core",
                                    },
                                    "name": "foo",
                                },
                                "spec": {
                                    "forProvider": {
                                        "tags": {
                                            "foo": "bar",
                                        }
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_ENV_TO_LABEL: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={
                                            "region.region": structpb.Value(
                                                string_value="regionName"
                                            ),
                                            "region.regionCode": structpb.Value(
                                                string_value="regionCode"
                                            ),
                                        }
                                    )
                                ),
                                c.INPUT_LABELS: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={c.INPUT_PREFIX: structpb.Value(string_value="bb")}
                                    )
                                ),
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="region.regionCode"),
                                            structpb.Value(string_value="ls-domain"),
                                        ]
                                    )
                                ),
                                c.INPUT_TAGS_FIELD: structpb.Value(string_value="awsTags"),
                            }
                        )
                    )
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {
                                        "do-not-delete": "me",
                                    },
                                    "name": "usw2-core-foo",
                                    "labels": {
                                        "bb/region": "us-west-2",
                                        "bb/region-code": "usw2",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "tags": {
                                            "environment": "Development",
                                            "foo": "bar",
                                            "owner": "Team A",
                                        }
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="The function should be able to tag resources from function input.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {
                                        "do-not-delete": "me",
                                        f"{PREFIX}account": "bar",
                                        f"{PREFIX}ls-domain": "core",
                                    },
                                    "name": "foo",
                                },
                                "spec": {
                                    "forProvider": {
                                        "tags": {
                                            "foo": "bar",
                                        }
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_ENV_TO_LABEL: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={
                                            "region.region": structpb.Value(
                                                string_value="regionName"
                                            ),
                                            "region.regionCode": structpb.Value(
                                                string_value="regionCode"
                                            ),
                                        }
                                    )
                                ),
                                c.INPUT_LABELS: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={c.INPUT_PREFIX: structpb.Value(string_value="bb")}
                                    )
                                ),
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="region.regionCode"),
                                            structpb.Value(string_value="ls-domain"),
                                        ]
                                    )
                                ),
                                c.INPUT_TAGS: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={
                                            "environment": structpb.Value(string_value="Testing"),
                                            "managed-by": structpb.Value(string_value="Crossplane"),
                                        }
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {
                                        "do-not-delete": "me",
                                    },
                                    "name": "usw2-core-foo",
                                    "labels": {
                                        "bb/region": "us-west-2",
                                        "bb/region-code": "usw2",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "tags": {
                                            "environment": "Testing",
                                            "foo": "bar",
                                            "managed-by": "Crossplane",
                                        }
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="The function should be able to read custom format from Inputs.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_ENV_TO_LABEL: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={
                                            "accountCode": structpb.Value(
                                                string_value="account-code"
                                            ),
                                            "namePrefix": structpb.Value(
                                                string_value="name-prefix"
                                            ),
                                            "region.regionCode": structpb.Value(
                                                string_value="region-code"
                                            ),
                                        }
                                    )
                                ),
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="name-prefix-tenant"),
                                            structpb.Value(string_value="account-code"),
                                            structpb.Value(string_value="region.regionCode"),
                                            structpb.Value(string_value="free-text"),
                                        ]
                                    )
                                ),
                                c.INPUT_LABELS: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={c.INPUT_PREFIX: structpb.Value(string_value="aa")}
                                    )
                                ),
                                c.INPUT_TEMPLATE_ITEMS_SEPARATOR: structpb.Value(string_value="."),
                            }
                        )
                    )
                }
            ),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "name": "foo",
                                    "annotations": {
                                        f"{PREFIX}free-text": "baz",
                                        f"{PREFIX}name-prefix-tenant": "aa",
                                        f"{c.ANNOTATION_INCLUDE_FORPROVIDER_NAME}": "true",
                                        f"{c.ANNOTATION_FORPROVIDER_NAMEOVERRIDE}": "true",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "hey",
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {},
                                    "name": "aa.tst.usw2.baz.foo",
                                    "labels": {
                                        "aa/account-code": "tst",
                                        "aa/name-prefix": "aa-tst-usw2",
                                        "aa/region-code": "usw2",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "aa.tst.usw2.baz.foo",
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="The function should be able to use mapped Values.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="name-prefix"),
                                            structpb.Value(string_value="domain"),
                                            structpb.Value(string_value="kind-code"),
                                        ]
                                    )
                                ),
                                # This is a list of structs with fields from, to and map
                                c.INPUT_MAPPED_VALUES: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(
                                                struct_value=structpb.Struct(
                                                    fields={
                                                        "fallback": structpb.Value(
                                                            string_value="void"
                                                        ),
                                                        "from": structpb.Value(string_value="kind"),
                                                        "maxLength": structpb.Value(number_value=9),
                                                        "to": structpb.Value(
                                                            string_value="kindCode"
                                                        ),
                                                        "map": structpb.Value(
                                                            struct_value=structpb.Struct(
                                                                fields={
                                                                    "XTest": structpb.Value(
                                                                        string_value="xt"
                                                                    )
                                                                }
                                                            )
                                                        ),
                                                    }
                                                )
                                            ),
                                        ]
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "name": "foo",
                                    "annotations": {
                                        f"{PREFIX}domain": "baz",
                                        f"{c.ANNOTATION_INCLUDE_TAG_NAME_ANNOTATION}": "true",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "hey",
                                        "tags": {},
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {},
                                    "name": "aa-tst-usw2-baz-xt-foo",
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "hey",
                                        "tags": {
                                            "Name": "aa-tst-usw2-baz-xt-foo",
                                        },
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="Per-resource kind code is not masked by mapped ones.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="name-prefix"),
                                            structpb.Value(string_value="domain"),
                                            structpb.Value(string_value="kind-code"),
                                        ]
                                    )
                                ),
                                # This is a list of structs with fields from, to and map
                                c.INPUT_MAPPED_VALUES: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(
                                                struct_value=structpb.Struct(
                                                    fields={
                                                        "fallback": structpb.Value(
                                                            string_value="void"
                                                        ),
                                                        "from": structpb.Value(string_value="kind"),
                                                        "maxLength": structpb.Value(number_value=9),
                                                        "to": structpb.Value(
                                                            string_value="kindCode"
                                                        ),
                                                        "map": structpb.Value(
                                                            struct_value=structpb.Struct(
                                                                fields={
                                                                    "XTest": structpb.Value(
                                                                        string_value="xt"
                                                                    )
                                                                }
                                                            )
                                                        ),
                                                    }
                                                )
                                            ),
                                        ]
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "name": "foo",
                                    "annotations": {
                                        f"{PREFIX}domain": "baz",
                                        f"{c.ANNOTATION_INCLUDE_TAG_NAME_ANNOTATION}": "true",
                                        f"{PREFIX}kindCode": "qux",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "hey",
                                        "tags": {},
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {},
                                    "name": "aa-tst-usw2-baz-qux-foo",
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "hey",
                                        "tags": {
                                            "Name": "aa-tst-usw2-baz-qux-foo",
                                        },
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="The function must always return an RFC1123 compliant metadata.name",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="name-prefix"),
                                            structpb.Value(string_value="kind-code"),
                                        ]
                                    )
                                ),
                                # This is a list of structs with fields from, to and map
                                c.INPUT_MAPPED_VALUES: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(
                                                struct_value=structpb.Struct(
                                                    fields={
                                                        "from": structpb.Value(string_value="kind"),
                                                        "to": structpb.Value(
                                                            string_value="kindCode"
                                                        ),
                                                        "map": structpb.Value(
                                                            struct_value=structpb.Struct(
                                                                fields={
                                                                    "XTest": structpb.Value(
                                                                        string_value="xt"
                                                                    )
                                                                }
                                                            )
                                                        ),
                                                    }
                                                )
                                            ),
                                        ]
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "name": "foo_bar",
                                    "annotations": {
                                        f"{c.ANNOTATION_INCLUDE_TAG_NAME_ANNOTATION}": "true",
                                        f"{c.ANNOTATION_INCLUDE_FORPROVIDER_NAME}": "true",
                                        f"{c.ANNOTATION_FORPROVIDER_NAMEOVERRIDE}": "true",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "hey",
                                        "tags": {
                                            "custom-tag": "custom-value",
                                        },
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {},
                                    "name": "aa-tst-usw2-xt-foo-bar",
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "aa-tst-usw2-xt-foo_bar",
                                        "tags": {
                                            "Name": "aa-tst-usw2-xt-foo_bar",
                                            "custom-tag": "custom-value",
                                        },
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="The function must be able to write in any field of the spec.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="name-prefix"),
                                            structpb.Value(string_value="kind-code"),
                                        ]
                                    )
                                ),
                                # This is a list of structs with fields from, to and map
                                c.INPUT_MAPPED_VALUES: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(
                                                struct_value=structpb.Struct(
                                                    fields={
                                                        "from": structpb.Value(string_value="kind"),
                                                        "to": structpb.Value(
                                                            string_value="kindCode"
                                                        ),
                                                        "map": structpb.Value(
                                                            struct_value=structpb.Struct(
                                                                fields={
                                                                    "XTest": structpb.Value(
                                                                        string_value="xt"
                                                                    )
                                                                }
                                                            )
                                                        ),
                                                    }
                                                )
                                            ),
                                        ]
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "name": "foo_bar",
                                    "annotations": {
                                        f"{c.ANNOTATION_INCLUDE_TAG_NAME_ANNOTATION}": "true",
                                        f"{c.ANNOTATION_INCLUDE_FORPROVIDER_NAME}": "true",
                                        f"{c.ANNOTATION_FORPROVIDER_NAME_FIELD}": "cluster.name",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "tags": {
                                            "custom-tag": "custom-value",
                                        },
                                    },
                                },
                            }
                        )
                    ),
                    "resource-b": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "name": "foo_bar",
                                    "annotations": {
                                        f"{c.ANNOTATION_INCLUDE_TAG_NAME_ANNOTATION}": "true",
                                        f"{c.ANNOTATION_INCLUDE_FORPROVIDER_NAME}": "true",
                                        f"{c.ANNOTATION_FORPROVIDER_NAME_FIELD}": "clusterName",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "tags": {
                                            "custom-tag": "custom-value",
                                        },
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {},
                                    "name": "aa-tst-usw2-xt-foo-bar",
                                },
                                "spec": {
                                    "forProvider": {
                                        "cluster": {
                                            "name": "aa-tst-usw2-xt-foo_bar",
                                        },
                                        "tags": {
                                            "Name": "aa-tst-usw2-xt-foo_bar",
                                            "custom-tag": "custom-value",
                                        },
                                    },
                                },
                            },
                        )
                    ),
                    "resource-b": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {},
                                    "name": "aa-tst-usw2-xt-foo-bar",
                                },
                                "spec": {
                                    "forProvider": {
                                        "clusterName": "aa-tst-usw2-xt-foo_bar",
                                        "tags": {
                                            "Name": "aa-tst-usw2-xt-foo_bar",
                                            "custom-tag": "custom-value",
                                        },
                                    },
                                },
                            },
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="Tags shouldn't be written if the resource doesn't support.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="name-prefix"),
                                        ]
                                    )
                                ),
                                c.INPUT_ENV_TO_LABEL: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="namePrefix"),
                                        ]
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
            desired=fnv1.State(
                resources={
                    "supports-tags": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "name": "foo",
                                    "annotations": {
                                        f"{c.ANNOTATION_INCLUDE_LABELS_AS_TAGS}": "true",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "hey",
                                        "tags": {},
                                    },
                                },
                            }
                        )
                    ),
                    "does-not-support-tags": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "name": "bar",
                                    "annotations": {
                                        f"{c.ANNOTATION_INCLUDE_LABELS_AS_TAGS}": "true",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "hey",
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "supports-tags": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {},
                                    "labels": {
                                        "name-prefix": "aa-tst-usw2",
                                    },
                                    "name": "aa-tst-usw2-foo",
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "hey",
                                        "tags": {
                                            "name-prefix": "aa-tst-usw2",
                                        },
                                    },
                                },
                            }
                        )
                    ),
                    "does-not-support-tags": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {},
                                    "labels": {
                                        "name-prefix": "aa-tst-usw2",
                                    },
                                    "name": "aa-tst-usw2-bar",
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "hey",
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="Don't fail when resource doesn't have metadata field.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="name-prefix"),
                                        ]
                                    )
                                ),
                                c.INPUT_ENV_TO_LABEL: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="namePrefix"),
                                        ]
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
            desired=fnv1.State(
                resources={
                    "missing-metadata": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "spec": {
                                    "forProvider": {
                                        "name": "foo",
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "missing-metadata": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "labels": {
                                        "name-prefix": "aa-tst-usw2",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "name": "foo",
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="Propagate labels to field.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="name-prefix"),
                                        ]
                                    )
                                ),
                                c.INPUT_ENV_TO_LABEL: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="namePrefix"),
                                        ]
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
            desired=fnv1.State(
                resources={
                    "missing-metadata": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "kubernetes.crossplane.io/v1alpha2",
                                "kind": "Object",
                                "metadata": {
                                    "annotations": {
                                        f"{c.ANNOTATION_REPLICATE_LABELS_TO}": "spec.forProvider.manifest.metadata.labels",
                                    },
                                    "name": "foo",
                                },
                                "spec": {
                                    "forProvider": {
                                        "manifest": {
                                            "apiVersion": "v1",
                                            "kind": "ConfigMap",
                                            "metadata": {
                                                "namespace": "default",
                                            },
                                        },
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "missing-metadata": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "kubernetes.crossplane.io/v1alpha2",
                                "kind": "Object",
                                "metadata": {
                                    "annotations": {},
                                    "name": "aa-tst-usw2-foo",
                                    "labels": {
                                        "name-prefix": "aa-tst-usw2",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "manifest": {
                                            "apiVersion": "v1",
                                            "kind": "ConfigMap",
                                            "metadata": {
                                                "namespace": "default",
                                                "labels": {
                                                    "name-prefix": "aa-tst-usw2",
                                                },
                                            },
                                        },
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="A resource annotations does not affect others.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="name-prefix"),
                                        ]
                                    )
                                ),
                                c.INPUT_ENV_TO_LABEL: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="namePrefix"),
                                        ]
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
            desired=fnv1.State(
                resources={
                    "missing-metadata": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "kubernetes.crossplane.io/v1alpha2",
                                "kind": "Object",
                                "metadata": {
                                    "annotations": {
                                        f"{c.ANNOTATION_REPLICATE_LABELS_TO}": "spec.forProvider.manifest.metadata.labels",
                                    },
                                    "name": "foo",
                                },
                                "spec": {
                                    "forProvider": {
                                        "manifest": {
                                            "apiVersion": "v1",
                                            "kind": "ConfigMap",
                                            "metadata": {
                                                "namespace": "default",
                                            },
                                        },
                                    },
                                },
                            }
                        )
                    ),
                    "should-be-ignored": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "kubernetes.crossplane.io/v1alpha2",
                                "kind": "Object",
                                "metadata": {
                                    "name": "bar",
                                },
                                "spec": {
                                    "forProvider": {
                                        "manifest": {
                                            "apiVersion": "v1",
                                            "kind": "ConfigMap",
                                            "metadata": {
                                                "namespace": "default",
                                            },
                                        },
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "missing-metadata": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "kubernetes.crossplane.io/v1alpha2",
                                "kind": "Object",
                                "metadata": {
                                    "annotations": {},
                                    "name": "aa-tst-usw2-foo",
                                    "labels": {
                                        "name-prefix": "aa-tst-usw2",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "manifest": {
                                            "apiVersion": "v1",
                                            "kind": "ConfigMap",
                                            "metadata": {
                                                "namespace": "default",
                                                "labels": {
                                                    "name-prefix": "aa-tst-usw2",
                                                },
                                            },
                                        },
                                    },
                                },
                            }
                        )
                    ),
                    "should-be-ignored": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "kubernetes.crossplane.io/v1alpha2",
                                "kind": "Object",
                                "metadata": {
                                    "labels": {
                                        "name-prefix": "aa-tst-usw2",
                                    },
                                    "name": "aa-tst-usw2-bar",
                                },
                                "spec": {
                                    "forProvider": {
                                        "manifest": {
                                            "apiVersion": "v1",
                                            "kind": "ConfigMap",
                                            "metadata": {
                                                "namespace": "default",
                                            },
                                        },
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="Labels as tag annotation overrides input.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_LABELS: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={
                                            c.INPUT_LABELS_AS_TAGS: structpb.Value(
                                                string_value="true"
                                            )
                                        }
                                    )
                                ),
                                c.INPUT_ENV_TO_LABEL: structpb.Value(
                                    struct_value=structpb.Struct(
                                        fields={
                                            "accountCode": structpb.Value(
                                                string_value="accountCode"
                                            ),
                                            "namePrefix": structpb.Value(string_value="namePrefix"),
                                            "region.regionCode": structpb.Value(
                                                string_value="regionCode"
                                            ),
                                        }
                                    )
                                ),
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="name-prefix"),
                                        ]
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
            desired=fnv1.State(
                resources={
                    "gimme-some-tags": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "kubernetes.crossplane.io/v1alpha2",
                                "kind": "Object",
                                "metadata": {
                                    "name": "foo",
                                },
                                "spec": {
                                    "forProvider": {
                                        "manifest": {
                                            "apiVersion": "v1",
                                            "kind": "ConfigMap",
                                            "metadata": {
                                                "namespace": "default",
                                            },
                                        },
                                        "tags": {},
                                    },
                                },
                            }
                        )
                    ),
                    "no-tags-please": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "kubernetes.crossplane.io/v1alpha2",
                                "kind": "Object",
                                "metadata": {
                                    "annotations": {
                                        f"{c.ANNOTATION_INCLUDE_LABELS_AS_TAGS}": "false",
                                    },
                                    "name": "bar",
                                },
                                "spec": {
                                    "forProvider": {
                                        "manifest": {
                                            "apiVersion": "v1",
                                            "kind": "ConfigMap",
                                            "metadata": {
                                                "namespace": "default",
                                            },
                                        },
                                        "tags": {},
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "gimme-some-tags": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "kubernetes.crossplane.io/v1alpha2",
                                "kind": "Object",
                                "metadata": {
                                    "name": "aa-tst-usw2-foo",
                                    "labels": {
                                        "account-code": "tst",
                                        "name-prefix": "aa-tst-usw2",
                                        "region-code": "usw2",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "manifest": {
                                            "apiVersion": "v1",
                                            "kind": "ConfigMap",
                                            "metadata": {
                                                "namespace": "default",
                                            },
                                        },
                                        "tags": {
                                            "account-code": "tst",
                                            "name-prefix": "aa-tst-usw2",
                                            "region-code": "usw2",
                                        },
                                    },
                                },
                            }
                        )
                    ),
                    "no-tags-please": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "kubernetes.crossplane.io/v1alpha2",
                                "kind": "Object",
                                "metadata": {
                                    "annotations": {},
                                    "name": "aa-tst-usw2-bar",
                                    "labels": {
                                        "account-code": "tst",
                                        "name-prefix": "aa-tst-usw2",
                                        "region-code": "usw2",
                                    },
                                },
                                "spec": {
                                    "forProvider": {
                                        "manifest": {
                                            "apiVersion": "v1",
                                            "kind": "ConfigMap",
                                            "metadata": {
                                                "namespace": "default",
                                            },
                                        },
                                        "tags": {},
                                    },
                                },
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
]

TESTEXCEPTIONS = [
    TestCase(
        reason="The function should abort when name items are missing and leave resource unchanged.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {
                                        "do-not-delete": "me",
                                        f"{PREFIX}account": "bar",
                                        f"{PREFIX}ls-domain": "core",
                                    },
                                    "name": "foo",
                                },
                                "spec": {},
                            }
                        )
                    ),
                }
            ),
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_NAME_TEMPLATE: structpb.Value(
                                    list_value=structpb.ListValue(
                                        values=[
                                            structpb.Value(string_value="non-existing-field"),
                                            structpb.Value(string_value="ls-domain"),
                                        ]
                                    )
                                ),
                            }
                        )
                    )
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "annotations": {
                                        "do-not-delete": "me",
                                        f"{PREFIX}account": "bar",
                                        f"{PREFIX}ls-domain": "core",
                                    },
                                    "name": "foo",
                                },
                                "spec": {},
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
    TestCase(
        reason="The function should abort when the context is missing.",
        req=fnv1.RunFunctionRequest(
            context=CONTEXT,
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "name": "foo",
                                },
                                "spec": {},
                            }
                        )
                    ),
                }
            ),
            input=structpb.Struct(
                fields={
                    "spec": structpb.Value(
                        struct_value=structpb.Struct(
                            fields={
                                c.INPUT_CONTEXT: structpb.Value(
                                    string_value="non-existing-context"
                                ),
                            }
                        )
                    )
                }
            ),
        ),
        want=fnv1.RunFunctionResponse(
            meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
            desired=fnv1.State(
                resources={
                    "resource-a": fnv1.Resource(
                        resource=resource.dict_to_struct(
                            {
                                "apiVersion": "example.crossplane.io/v1alpha1",
                                "kind": "XTest",
                                "metadata": {
                                    "name": "foo",
                                },
                                "spec": {},
                            }
                        )
                    ),
                }
            ),
            context=CONTEXT,
        ),
    ),
]


class TestRunner(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        # Allow larger diffs, since we diff large strings of JSON.
        self.maxDiff = None
        logging.configure(level=logging.Level.DISABLED)

    async def test_run_function(self) -> None:
        runner = fn.Runner()
        for i, case in enumerate(TESTCASES):
            got = await runner.RunFunction(case.req, None)
            self.assertEqual(
                json_format.MessageToDict(case.want),
                json_format.MessageToDict(got),
                msg=f"Failed for test number {i}: '{case.reason}' (-want, +got)",
            )

    async def test_exceptions(self) -> None:
        runner = fn.Runner()
        mock_context = mock.AsyncMock(spec=grpc.aio.ServicerContext)
        for i, case in enumerate(TESTEXCEPTIONS):
            got = await runner.RunFunction(case.req, mock_context)
            mock_context.abort.assert_called()
            self.assertEqual(
                json_format.MessageToDict(case.want),
                json_format.MessageToDict(got),
                msg=f"Failed for test number {i}: '{case.reason}' (-want, +got)",
            )


if __name__ == "__main__":
    unittest.main()
