# Kubernetes base

This Kustomize base runs the locally built `humorvibes-research:0.6.0` image in offline/hash mode.
It is intentionally a `ClusterIP` service with no Ingress and no committed Secret.

```bash
docker build -t humorvibes-research:0.6.0 .
kind load docker-image humorvibes-research:0.6.0
kubectl apply -k deploy/kubernetes
kubectl rollout status deployment/humorvibes
kubectl port-forward service/humorvibes 8080:80
```

Create the optional `humorvibes-secrets` Secret before any external exposure. Use a
deployment-specific Kustomize overlay to set an immutable registry digest, ingress/TLS, network
policy, external-secret integration, autoscaling, and provider configuration. Full commands and
the environment reference are in [`../../docs/API_AND_DEPLOYMENT.md`](../../docs/API_AND_DEPLOYMENT.md).
