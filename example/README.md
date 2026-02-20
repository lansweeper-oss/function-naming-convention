# Example manifests

You can run your function locally and test it using `crossplane beta render`
with these example manifests.

> CI runs this very same command to validate and check differences between commits

```shell
# Run the function locally
$ make run

# or
$ hatch run development
```

Then, in another terminal, call it with these example manifests:

```shell
$ cd example
$ crossplane render -rx -e context.yaml xr.yaml composition.yaml functions.yaml
---
apiVersion: example.crossplane.io/v1
kind: XR
metadata:
  name: example-xr
spec:
  forProvider:
    region: eu-south-1
  parameters:
    cidrBlock: 10.196.10.0/24
status:
  conditions:
  - lastTransitionTime: "2024-01-01T00:00:00Z"
    message: 'Unready resources: vpc'
    reason: Creating
    status: "False"
    type: Ready
---
apiVersion: ec2.aws.upbound.io/v1beta1
kind: VPC
metadata:
  annotations:
    crossplane.io/composition-resource-name: vpc
    custom-annotation: keep-me
  generateName: example-xr-
  labels:
    crossplane.io/composite: example-xr
    ac/account: testing
    ac/account-code: tst
    ac/account-id: "000987654321"
    ac/region: eu-south-2
    ac/region-code: eus2
    ac/tenant: acme
  name: ac-tst-eus2-vpc-foo
  ownerReferences:
  - apiVersion: example.crossplane.io/v1
    blockOwnerDeletion: true
    controller: true
    kind: XR
    name: example-xr
    uid: ""
spec:
  forProvider:
    cidrBlock: 10.196.10.0/24
    enableDnsHostnames: true
    enableDnsSupport: true
    name: ac-tst-eus2-vpc-foo
    region: eu-south-2
    tags:
      Name: ac-tst-eus2-vpc-foo
      ac/account: testing
      ac/domain: core
      ac/environment: testing
      ac/owner: the-a-team
      ac/region: eu-south-2
      static-tag: baz
```
