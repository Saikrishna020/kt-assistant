from __future__ import annotations

from repo_intelligence.models.service import Service

BUSINESS_HINTS = {
    "checkoutservice",
    "cartservice",
    "productcatalogservice",
    "paymentservice",
    "shippingservice",
    "recommendationservice",
    "currencyservice",
    "emailservice",
    "adservice",
    "frontend",
    "shoppingassistantservice",
}

SUPPORTING_HINTS = {
    "loadgenerator",
    "gateway",
    "bff",
    "ui",
    "frontend-external",
}

INFRA_HINTS = {
    "redis",
    "redis-cart",
    "opentelemetrycollector",
    "otel",
    "prometheus",
    "grafana",
    "jaeger",
    "kafka",
    "rabbitmq",
    "zookeeper",
    "nginx",
}


def classify_component(service: Service) -> tuple[str, float, str]:
    name = service.name.lower()
    source = service.source.lower()
    path = service.path.lower()
    api_count = len(service.apis)

    if "external" in name or "canary" in name or "staging" in name:
        return "deployment_variant", 0.9, "name indicates deployment variant"

    if name in INFRA_HINTS or any(hint in name for hint in INFRA_HINTS):
        return "infrastructure_component", 0.9, "name matches infrastructure hint"

    if "kustomize/components" in path and api_count == 0:
        return "infrastructure_component", 0.82, "component path indicates infrastructure helper"

    if name in SUPPORTING_HINTS or any(hint in name for hint in SUPPORTING_HINTS):
        return "supporting_component", 0.78, "name matches supporting component hint"

    if name in BUSINESS_HINTS:
        return "business_service", 0.88, "name matches common business-service naming"

    if api_count > 0 and service.runtime != "unknown":
        return "business_service", 0.82, "runtime + API presence indicates business service"

    if "kubernetes-manifests" in source and api_count == 0 and service.runtime == "unknown":
        return "unknown_artifact", 0.65, "manifest-only detection without source/runtime evidence"

    if api_count > 0:
        return "supporting_component", 0.7, "API presence without stronger business signal"

    return "unknown_artifact", 0.55, "insufficient evidence for stronger classification"


def classify_services(services: list[Service]) -> list[Service]:
    for service in services:
        component_type, classification_confidence, reason = classify_component(service)
        service.component_type = component_type
        service.classification_confidence = classification_confidence
        service.classification_reason = reason
    return services
