"""A Crossplane composition function to enforce Naming convention adoption.

This function loads environment data and mutates all resources of a composition
to have a proper name, labels and (optionally) tags.
"""

import asyncio
from copy import deepcopy

import grpc
from caseconverter import camelcase, kebabcase
from crossplane.function import logging, resource, response
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from crossplane.function.proto.v1 import run_function_pb2_grpc as grpcv1
from google.protobuf import message
from google.protobuf import struct_pb2 as structpb

import function.constants as c


def _dot_notation_to_struct_field(
    struct: structpb.Struct,
    path: str,
) -> structpb.Struct | None:
    """Get a reference to a field from a Struct using dot notation.

    It does not return the field contents, but the struct reference to it.
    """
    first, _, rest = path.partition(".")
    if rest and (first in struct):
        return _dot_notation_to_struct_field(struct[first], rest)
    elif first in struct:
        return struct


def _dot_notation_to_struct_field_create_if_not_existing(
    struct: structpb.Struct,
    path: str,
    constructor: any,
) -> structpb.Struct:
    """Get a reference to a field from a Struct using dot notation.

    If the field does not exist, it will be created based on the constructor.
    It does not return the field contents, but the struct reference to it.
    """
    res = _dot_notation_to_struct_field(struct, path)
    if not res:
        # Create the field if it does not exist
        first, _, rest = path.partition(".")
        if first not in struct:
            if "." in rest:
                struct.update({first: resource.struct_to_dict({rest.split(".")[0]: {}})})
            elif rest:
                struct.update({first: {rest: constructor}})
            else:
                struct.update({first: constructor})
                return struct[first] if isinstance(constructor, dict) else struct
            return struct[first]
        return _dot_notation_to_struct_field_create_if_not_existing(
            struct[first],
            rest,
            constructor=constructor,
        )
    return res


def _get_resource_kind_and_name(res: structpb.Struct) -> tuple[str | None, str | None]:
    """Get the kind and name of a resource."""
    kind = res["kind"] if "kind" in res else None
    name = res["metadata"]["name"] if "metadata" in res and "name" in res["metadata"] else None
    return kind, name


def _get_struct_field_using_dot_notation(
    struct: structpb.Struct, path: str
) -> tuple[str, str] | None:
    """Get a field from a Struct using dot notation.

    Returns a tuple of (field_key, field_value) or None if not found.
    """
    ref = _dot_notation_to_struct_field(struct, path)
    sub_path = path.rsplit(".", maxsplit=1)[-1]
    if ref and sub_path in ref:
        f = ref[sub_path]
        if f:
            return (sub_path, str(f))
    return None


def _to_rfc952_name(
    name: str, max_length=c.MAX_NAME_LENGTH, replace_if_not_valid="-", valid_chars=(".", "-")
) -> str:
    """Ensure that a name is RFC 952 compliant.

    That is, it only contains alphanumeric characters and hyphens. RFC952 restrictions about the
    length are optional here, since RFC 1123 is less restrictive than RFC 952 in that regard.
    When a character is not valid, it is replaced with a hyphen.
    """
    sanitized = "".join(
        char if (char.isalnum() or char in valid_chars) else replace_if_not_valid for char in name
    )
    return sanitized.strip(replace_if_not_valid)[:max_length]


class Resource:
    """Resource is a wrapper around a resource with a resource-specific environment."""

    def __init__(self, environment: dict, name: str, res: structpb.Struct):
        """Create a new Resource."""
        self.environment = deepcopy(environment)
        if "metadata" in res:
            self.metadata = deepcopy(resource.struct_to_dict(res["metadata"]))
        else:
            self.metadata = {}
        self.ref = name
        self.resource = res
        self.result = deepcopy(resource.struct_to_dict(res))


class Runner(grpcv1.FunctionRunnerService):
    """A Runner handles gRPC RunFunctionRequests."""

    def __init__(self):
        """Create a new FunctionRunner."""
        self.annotation_prefix = ""
        self.input = {}
        self.label_prefix = ""
        self.kebab_cased_labels_and_tags = True
        self.log = logging.get_logger()
        self.log.info("Starting function-naming-convention")

    @staticmethod
    def _check_if_true(data: dict, name: str, *, default: bool = False) -> bool:
        """Check if an item from a dictionary is true-ish."""
        return data.get(name, str(default)).lower() in {
            "on",
            "true",
            "y",
            "yes",
        }

    @staticmethod
    def _format_name_prefix(
        environment: dict,
        name_prefix_items: list[str],
        separator: str,
    ) -> str:
        """Format the name prefix using the resource environment."""
        env = deepcopy(environment)
        # First check if any of the name_prefix_items keys are in dot notation
        for item in filter(lambda i: "." in i, name_prefix_items):
            result = _get_struct_field_using_dot_notation(env, item)
            if result:
                _, value = result
                if value:
                    env[camelcase(item)] = value
        formatted_items = []
        for i in name_prefix_items:
            item = camelcase(i)
            if item not in env:
                # Fail if any of the items is missing in order not to have a resource recreated in
                # case the environment changes
                msg = f"Failed to render name prefix from environment; missing key '{item}'"
                raise message.EncodeError(msg)
            formatted_items.append(env[item])
        return separator.join(formatted_items)

    def _sanitize_label(self, name: str) -> str:
        """Sanitize a label key to be RFC 1123 compliant.

        Valid label keys have two segments: an optional prefix and name, separated by a slash (/).
        The name segment is required and must be 63 characters or less, beginning and ending with an
        alphanumeric character ([a-z0-9A-Z]) with dashes (-), underscores (_), dots (.), and
        alphanumerics between.

        The prefix is optional. If specified, the prefix must be a DNS subdomain: a series of DNS
        names separated by dots (.), not longer than 253 characters in total,
        followed by a slash (/).

        Optionally it enforces kebab-case for the name segment.
        """
        prefix = ""
        if "/" in name:
            prefix, name = name.split("/", 1)
            # Truncate prefix if larger than 253 - 1 (for the slash) - 63 (for the name)
            max_prefix_length = c.MAX_PREFIXED_NAME_LENGTH - 1 - c.MAX_NAME_LENGTH
            prefix = _to_rfc952_name(prefix, max_length=max_prefix_length, valid_chars=("."))
        name = _to_rfc952_name(
            kebabcase(name) if self.kebab_cased_labels_and_tags else name,
            valid_chars=("-") if self.kebab_cased_labels_and_tags else ("-", "_", "."),
        )
        return prefix + "/" + name if prefix else name

    @staticmethod
    def _sanitized_name(name: str) -> str:
        """Sanitize a name to be lowercase RFC 1123 subdomain compliant."""
        return _to_rfc952_name(name, valid_chars=("-", ".")).lower()

    async def _cleanup_fn_specific_annotations(
        self,
        res: Resource,
    ) -> None:
        """Cleanup function-specific annotations.

        The function-specific annotations will be removed from the metadata,
        so the ending resource does not include them.
        """
        try:
            metadata = deepcopy(res.metadata)
            for annotation in res.metadata.get("annotations", {}):
                if annotation.startswith(self.annotation_prefix):
                    metadata["annotations"].pop(annotation)
            res.metadata = metadata
        except Exception as exc:
            self.log.error(f"Failed to cleanup annotations: {exc!r}")

    def _get_from_annotation_or_input(
        self, res: Resource, annotation_field: str, input_field: str, default: str = ""
    ) -> str:
        """Get a value from a Resource annotation or input if not present.

        Function inputs can be of two types, global and per resource. How those are read,
        ordered from highest to lowest precedence:
        - Resource annotation (resource-specific)
        - The Function input (global to all resources)
        - Fallback (function) default

        That is, if a resource sets a specific format for the name, it will be used.
        Otherwise, the global format will be used.
        """
        annotations = res.metadata.get("annotations", {})
        return annotations.get(annotation_field, self.input.get(input_field, default))

    def _parse_annotations(self, res: Resource) -> None:
        """Get input from function-specific annotations."""
        for annotation, val in res.metadata.get("annotations", {}).items():
            if annotation.startswith(self.annotation_prefix):
                a = annotation[len(self.annotation_prefix) :]
                # Update internal environment too
                res.environment[camelcase(a)] = val

    def get_name(
        self,
        res: Resource,
        name: str | None,
    ) -> str:
        """Get the name for the resource as per the naming convention."""
        if not name:  # If name is not set, Crossplane will autogenerate it
            return name
        annotations = res.metadata.get("annotations", {})
        # Name prefix items and separator can be set from different sources.
        # The items both accept camelCase and kebab-case (e.g. both
        # `namePrefix` and `name-prefix` will be equivalent).
        name_items_separator = self._get_from_annotation_or_input(
            res,
            c.ANNOTATION_NAME_TEMPLATE_SEPARATOR,
            c.INPUT_TEMPLATE_ITEMS_SEPARATOR,
            default=c.DEFAULT_NAME_TEMPLATE_SEPARATOR,
        )
        fallback_name_items = self.input.get(c.INPUT_NAME_TEMPLATE, [])
        name_prefix_items = annotations.get(c.ANNOTATION_NAME_TEMPLATE, None)
        if name_prefix_items:
            name_prefix_items = name_prefix_items.split(c.ANNOTATION_NAME_TEMPLATE_SEPARATOR)
        else:
            name_prefix_items = fallback_name_items

        name_prefix = self._format_name_prefix(
            res.environment, name_prefix_items, name_items_separator
        )
        return (name_prefix + name_items_separator + name)[: c.MAX_NAME_LENGTH]

    def get_labels(self, res: Resource) -> dict:
        """Get the labels for the resource as per the naming convention."""
        labels = res.metadata.get("labels", {})
        # Update the metadata labels with the environment variables and ensure
        # that the label name is RFC 1123 compliant.
        # The list of which environment variables are mapped comes from the
        # c.INPUT_ENV_TO_LABEL field in the function input.
        self.log.debug("Mutating labels")
        for label in self.ENV_TO_LABEL:
            result = _get_struct_field_using_dot_notation(res.environment, label)
            if not result:
                self.log.debug(f"'{label}' not found in the context, skipping label mapping")
                continue
            key, value = result
            self.log.debug(f"Mapping env var '{label}' to label with value '{value}'")
            if value:
                label_key = self._sanitize_label(f"{self.label_prefix}{key}")
                labels[label_key] = _to_rfc952_name(value, valid_chars=("-", "_", "."))
        return labels

    async def mutate_external_name(self, res: Resource, new_name: str) -> None:
        """Conditionally set the external-name annotation for the resource."""
        try:
            annotations = res.metadata.get("annotations", {})
            if self._check_if_true(annotations, c.ANNOTATION_INCLUDE_EXTERNAL_NAME) and new_name:
                annotations.setdefault(
                    "crossplane.io/external-name",
                    new_name,
                )
                self.log.debug(f"Set external-name annotation to {new_name} for {res.ref}")
                res.metadata["annotations"] = annotations
        except Exception as exc:
            msg = f"Failed to set external-name annotation for {res.ref}: {exc!r}"
            raise message.EncodeError(msg) from exc

    async def mutate_forprovider_name(self, res: Resource, new_name: str) -> None:
        """Conditionally mutate the spec.forProvider.name for the resource."""
        try:
            annotations = res.metadata.get("annotations", {})
            for_provider_name_field = annotations.get(c.ANNOTATION_FORPROVIDER_NAME_FIELD, "name")
            if (
                self._check_if_true(annotations, c.ANNOTATION_INCLUDE_FORPROVIDER_NAME)
                and "spec" in res.resource
                and "forProvider" in res.resource["spec"]
            ):
                field_reference = _dot_notation_to_struct_field_create_if_not_existing(
                    res.resource["spec"]["forProvider"],
                    for_provider_name_field,
                    constructor="",
                )
                self.log.debug(f"Mutating forProvider.{for_provider_name_field} for {res.ref}")
                for_provider_name_field = for_provider_name_field.split(".")[-1]
                # We ignore the current value of spec.forProvider.name if we
                # are told to do so or if it is empty.
                if (
                    self._check_if_true(annotations, c.ANNOTATION_FORPROVIDER_NAMEOVERRIDE)
                    or not for_provider_name_field not in field_reference
                ):
                    field_reference[for_provider_name_field] = new_name
                else:
                    # Mutate existing value
                    field_reference[for_provider_name_field] = self.get_name(
                        res=res,
                        name=field_reference[for_provider_name_field],
                    )
        except Exception as exc:
            msg = f"Failed to mutate forProvider.{for_provider_name_field} for {res.ref}: {exc!r}"
            raise message.EncodeError(msg) from exc

    async def mutate_metadata(
        self,
        res: Resource,
        *,
        skip_name_modification: bool,
    ) -> str:
        """Modify the name and labels for the resource.

        Name is rendered according to {ANNOTATION,INPUT}_NAME_TEMPLATE.
        It will omit any missing value. If original name is not set, it will
        remain like that (Crossplane autogenerates the name).
        Metadata annotations may contain custom field variables starting
        with a given prefix. Both camelCase and kebab-case are supported.
        """
        self._parse_annotations(res)
        current_name = new_name = res.metadata.get("name", "")
        new_labels = self.get_labels(res)
        if new_labels.keys() != res.metadata.get("labels", {}).keys():
            self.log.debug(f"Mutating labels to {new_labels}")
            res.metadata["labels"] = new_labels
        if not skip_name_modification:
            new_name = self.get_name(
                res=res,
                name=current_name,
            )
            # metadata.name needs to be RFC1123 compliant, so even if the
            # Cloud provider name is not, we need to ensure it is.
            new_metadata_name = self._sanitized_name(new_name)
            if new_metadata_name != current_name:
                self.log.debug(f"Mutating name to {new_metadata_name}")
                res.metadata["name"] = new_metadata_name
        return new_name

    async def mutate_resource(
        self,
        res: Resource,
    ) -> structpb.Struct:
        """Mutate the resource to adhere the Naming convention."""
        for mapped_value in self.input.get(c.INPUT_MAPPED_VALUES, []):
            result = _get_struct_field_using_dot_notation(res.resource, mapped_value["from"])
            if not result:
                self.log.debug(
                    f"'{mapped_value['from']}' not found in the resource, skipping mapped value"
                )
                continue
            _, v = result
            if v:
                try:
                    value = mapped_value["map"][v]
                except KeyError:
                    fallback_mapped_value = mapped_value.get(
                        "fallback",
                        c.DEFAULT_MAPPED_VALUE,
                    )
                    mapped_value_field_max_length = mapped_value.get(
                        "maxLength",
                        c.DEFAULT_MAPPED_VALUE_MAX_LENGTH,
                    )
                    value = (
                        fallback_mapped_value
                        if len(v) > mapped_value_field_max_length
                        else v.lower()
                    )
                    self.log.debug(
                        f"No mapped value {v} from {mapped_value['from']}, falling back to {value}"
                    )
                res.environment[mapped_value["to"]] = str(value).lower()
        await self.run_mutations(res)
        await self._cleanup_fn_specific_annotations(res)
        # Finally dump the metadata back to the resource
        res.resource["metadata"] = resource.dict_to_struct(res.metadata)
        return res.resource

    async def mutate_tags(self, res: Resource, new_name: str) -> None:
        """Conditionally mutate the tags for the resource.

        Tags are set according to multiple sources, in order of precedence (last will override):
          - We first inject the tags from a 'tags' context field if set.
          - Then inject the tags from the function input (optional).
          - Then, we add the (mutated) 'Name' tag if configured to do so.
          - Finally, we copy over labels as tags if configured to do so.
        """
        if not (
            "spec" in res.resource
            and "forProvider" in res.resource["spec"]
            and "tags" in res.resource["spec"]["forProvider"]
        ):
            self.log.debug(f"No tags field found for {res.ref}, skipping tags mutation")
            return  # Not a resource that supports tags
        self.log.debug(f"Mutating tags for {res.ref}")
        annotations = res.metadata.get("annotations", {})
        tags = res.resource["spec"]["forProvider"]["tags"]
        # Set tags from 'tagsField' context key if set
        tags_field = self._get_from_annotation_or_input(
            res, c.ANNOTATION_TAGS_FIELD, c.INPUT_TAGS_FIELD
        )
        if res.environment.get(tags_field):
            self.log.debug(f"Injecting tags from context key {tags_field} for {res.ref}")
            try:
                tags.update(res.environment[tags_field])
            except ValueError:
                self.log.warning(f"Failed to set tags from context key {tags_field} for {res.ref}")
        # Inject tags from function input
        input_tags = self.input.get(c.INPUT_TAGS, {})
        if input_tags:
            self.log.debug(f"Injecting tags from function input for {res.ref}")
            try:
                tags.update(input_tags)
            except TypeError:
                self.log.warning(f"Failed to set tags from function input for {res.ref}")
        # Add Name tag if configured to do so
        if self._check_if_true(annotations, c.ANNOTATION_INCLUDE_TAG_NAME_ANNOTATION):
            try:
                self.log.debug(f"Mutating Name tag for {res.ref}")
                tags.update({"Name": new_name})
            except ValueError:
                self.log.warning(f"Failed to set Name tag for {res.ref}")
        # Copy labels as tags if configured to do so
        if self._check_if_true(
            annotations,
            c.ANNOTATION_INCLUDE_LABELS_AS_TAGS,
            default=self.input.get(c.INPUT_LABELS, {}).get(c.INPUT_LABELS_AS_TAGS, False),
        ):
            labels = self.get_labels(res=res)
            try:
                # Double-check we only copy the labels added by the Function
                self.log.debug(f"Copying labels to tags for {res.ref}")
                tags.update({k: v for k, v in labels.items() if k.startswith(self.label_prefix)})
            except ValueError:
                self.log.warning(f"Failed to set tags from labels for {res.ref}")

    async def process_resource(
        self,
        desired: structpb.Struct,
        parent: structpb.Struct,
        res: Resource,
    ) -> None:
        """Process a single resource."""
        if parent:
            xr_kind, xr_name = _get_resource_kind_and_name(parent)
            res.ref += f"@{xr_kind}/{xr_name}"
            self.log.debug(f"Processing resource {res.ref}")
        resource.update(
            desired,
            await self.mutate_resource(res=res),
        )

    async def read_environment(self, req: fnv1.RunFunctionRequest) -> None:
        """Read Context and the Function input.

        This context is shared by all resources of a composition, so we should never alter
        self.environment from resource annotations.
        """
        self.input = resource.struct_to_dict(req.input).get("spec", {})
        context = self.input.get(c.INPUT_CONTEXT, c.CONTEXT_KEY_ENVIRONMENT)
        # Handle context keys with multiple parts (e.g., "dns.domain/name/group")
        self.log.debug(f"Reading context from key: '{context}'")
        try:
            if context.count("/") > 1:
                context_gv, _, context_k = context.rpartition("/")
                request_context = req.context[context_gv][context_k]
            else:
                request_context = req.context[context]
            self.environment = resource.struct_to_dict(request_context)
        except (KeyError, ValueError) as exc:
            msg = f"Failed to read context '{context}': {exc!r}"
            self.log.error(msg)
            raise Exception(msg) from exc

        self.environment.update(self.input.get(c.INPUT_VALUES, {}))

        a_prefix = self.input.get(c.INPUT_ANNOTATIONS, {}).get(c.INPUT_PREFIX, c.ANNOTATION_PREFIX)
        a_separator = self.input.get(c.INPUT_ANNOTATIONS, {}).get(
            c.INPUT_SEPARATOR, c.DEFAULT_PREFIX_SEPARATOR
        )
        l_prefix = self.input.get(c.INPUT_LABELS, {}).get(c.INPUT_PREFIX, "")
        l_separator = self.input.get(c.INPUT_LABELS, {}).get(
            c.INPUT_SEPARATOR, c.DEFAULT_PREFIX_SEPARATOR
        )
        self.annotation_prefix = f"{a_prefix}{a_separator}" if a_prefix else ""
        self.label_prefix = f"{l_prefix}{l_separator}" if l_prefix else ""

        self.kebab_cased_labels_and_tags = self._check_if_true(
            self.input,
            c.INPUT_KEBAB_CASE_LABELS_AND_TAGS,
            default=self.kebab_cased_labels_and_tags,
        )

    async def replicate_labels(self, res: Resource) -> None:
        """Replicate labels from the resource's metadata to a given resource field."""
        try:
            field = res.metadata.get("annotations", {}).get(c.ANNOTATION_REPLICATE_LABELS_TO)
            if not field:
                return
            labels = res.metadata.get("labels", {})
            to = _dot_notation_to_struct_field_create_if_not_existing(res.resource, field, {})
            if labels and to is not None:
                to.update(labels)
        except Exception as exc:
            self.log.error(f"Failed to replicate labels to {field} for {res.ref}: {exc!r}")

    async def run_mutations(self, res: Resource) -> None:
        """Run all mutations on the resource."""
        # Skip name modification when configured to do so
        annotations = resource.struct_to_dict(res.resource.get_or_create_struct("metadata")).get(
            "annotations", {}
        )
        skip_name_modification = self._check_if_true(annotations, c.ANNOTATION_SKIP_NAME_MODIFY)
        new_name = await self.mutate_metadata(
            res=res,
            skip_name_modification=skip_name_modification,
        )
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.mutate_tags(res, new_name))
            tg.create_task(self.replicate_labels(res))
            tg.create_task(self.mutate_forprovider_name(res, new_name))
            tg.create_task(self.mutate_external_name(res, new_name))

    async def RunFunction(
        self, req: fnv1.RunFunctionRequest, context: grpc.aio.ServicerContext
    ) -> fnv1.RunFunctionResponse:
        """Run the function."""
        rsp = response.to(req)
        self.log.debug("Invoked function-naming-convention")
        try:
            await self.read_environment(req)

            # Populate which Environment variables should be mapped to labels
            self.ENV_TO_LABEL = self.input.get(c.INPUT_ENV_TO_LABEL, {})
            async with asyncio.TaskGroup() as tg:
                for name in req.desired.resources:
                    tg.create_task(
                        self.process_resource(
                            desired=rsp.desired.resources[name],
                            parent=req.observed.composite.resource,
                            res=Resource(
                                environment=self.environment,
                                name=name,
                                res=req.desired.resources[name].resource,
                            ),
                        )
                    )
        except* Exception as exc:
            # Every error that has to do with a resource name modification will raise an exception
            # which is handled here, so we return a proper gRPC error and stop the pipeline.
            # This way we ensure that a valid name is not modified afterwards if something goes
            # wrong or a context field is missing.
            # Thus, we treat name fields as immutable once set.
            xr_kind, xr_name = _get_resource_kind_and_name(req.observed.composite.resource)
            self.log.warning(f"Function failed to mutate resource {xr_kind}/{xr_name}: {exc!r}")
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, repr(exc))
        return rsp
