# Envoy Gateway production boundary

This opt-in example adds TLS 1.3 termination, edge API-key identity, local burst limiting, a
Redis-backed global quota, and trace-context forwarding in front of the internal `ClusterIP`
Service. It targets Envoy Gateway 1.8.3 and uses the documentation-reserved hostname
`api.humorvibes.example`; change that hostname only in a deployment-specific overlay.

The base application remains offline and default-deny on egress. Do not apply this directory as
part of the base Kustomization: a real cluster must name its gateway controller, DNS, certificate
issuer, secret manager, Redis, and telemetry collector first.

## Install and verify the example

Install the controller and enable its Redis-backed global rate-limit service:

```bash
helm upgrade --install eg oci://docker.io/envoyproxy/gateway-helm \
  --version v1.8.3 \
  --namespace envoy-gateway-system \
  --create-namespace \
  --set config.envoyGateway.rateLimit.backend.type=Redis \
  --set config.envoyGateway.rateLimit.backend.redis.url=redis.redis-system.svc.cluster.local:6379
```

The command assumes the platform team has already provisioned the named Redis service. Production
Redis needs persistence, authentication, availability, and a network policy; those choices do not
belong in an application repository.

Create a TLS key locally without committing it, then create both referenced Secrets:

```bash
gateway_tmp=$(mktemp -d)
openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 30 \
  -subj '/CN=api.humorvibes.example/O=HumorVibes local gateway test' \
  -addext 'subjectAltName=DNS:api.humorvibes.example' \
  -keyout "$gateway_tmp/tls.key" -out "$gateway_tmp/tls.crt"
kubectl create secret tls humorvibes-tls \
  --key "$gateway_tmp/tls.key" --cert "$gateway_tmp/tls.crt"

: "${HUMORVIBES_EDGE_API_KEY:?Set a non-empty edge API key}"
kubectl create secret generic humorvibes-edge-api-keys \
  --from-literal=integration-client="$HUMORVIBES_EDGE_API_KEY"
```

Apply the API and edge resources, then wait for accepted conditions:

```bash
kubectl apply -k deploy/kubernetes
kubectl apply -k deploy/gateway
kubectl wait --for=condition=Programmed gateway/humorvibes --timeout=180s
kubectl wait --for=condition=Accepted httproute/humorvibes --timeout=180s
kubectl get securitypolicy,backendtrafficpolicy,clienttrafficpolicy -o wide
```

Resolve the gateway address and test both rejection and acceptance. The self-signed certificate is
supplied explicitly rather than disabling TLS verification:

```bash
gateway_address=$(kubectl get gateway humorvibes -o jsonpath='{.status.addresses[0].value}')
curl --silent --output /dev/null --write-out '%{http_code}\n' \
  --resolve "api.humorvibes.example:443:$gateway_address" \
  --cacert "$gateway_tmp/tls.crt" \
  https://api.humorvibes.example/v1/capabilities
curl --fail --show-error \
  --resolve "api.humorvibes.example:443:$gateway_address" \
  --cacert "$gateway_tmp/tls.crt" \
  -H "x-api-key: $HUMORVIBES_EDGE_API_KEY" \
  -H 'traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01' \
  https://api.humorvibes.example/v1/capabilities
```

Envoy Gateway enforces the shared 600-request/minute rule only when its global rate-limit service
is healthy and configured with Redis. Check policy status and rate-limit service metrics before
calling the quota operational. Application spans can join the forwarded W3C trace when the API is
installed with the `telemetry` extra and `HUMORVIBES_OTEL_TRACES_ENDPOINT`; neither layer records
request/response bodies or authorization values.

For production, replace the self-signed certificate with cert-manager or the platform certificate
service, source keys from the cluster secret manager, use a real DNS name, and add only the exact
egress destinations required by the selected model and telemetry providers.
