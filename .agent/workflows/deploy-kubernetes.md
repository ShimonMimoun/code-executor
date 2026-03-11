---
description: Deploy Code Executor to Kubernetes or OpenShift using Helm
---
# Kubernetes Deployment Workflow

This workflow provides instructions for deploying the `code-executor` platform into a Kubernetes or OpenShift cluster using the provided Helm chart.

## Prerequisites
- Kubernetes cluster (or OpenShift, minikube, kind)
- `kubectl` configured and authenticated
- `helm` v3+ installed

## 1. Review Helm Values
Before deploying, review the chart's configuration. The chart bundles the API backend, an optional Redis instance, and an optional Frontend dashboard.

```bash
cat helm/code-executor/values.yaml
```

Key customizations often involve:
- Ingress/Route hostnames.
- `config` section (which defines the API's runtime TOML configuration).
- Toggling `redis.enabled` or `frontend.enabled`.

## 2. Prepare the Namespace

```bash
# Create the target namespace
kubectl create namespace code-executor

# Switch to the namespace to simplify subsequent commands
kubectl config set-context --current --namespace=code-executor
```

## 3. Install the Helm Chart
Run the `helm install` command from the root of the project directory.

```bash
helm install code-executor ./helm/code-executor/
```

To upgrade an existing installation when changes are made to the chart:
```bash
helm upgrade code-executor ./helm/code-executor/
```

## 4. Post-Install (OpenShift Specific)
If you are deploying on OpenShift and did not enable `route.enabled: true` in the `values.yaml`, you may need to expose the API service manually.

```bash
oc expose svc/code-executor-api
```

## 5. Verify the Deployment
Check that pods are spinning up successfully.

```bash
kubectl get pods -w
```
Wait until pods report `Running` and their containers are `Ready=1/1`.

You can view the backend logs specifically:
```bash
kubectl logs -l app.kubernetes.io/name=code-executor -l app.kubernetes.io/component=api -f
```
