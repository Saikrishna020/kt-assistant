from __future__ import annotations

from kt_ai.domain.models import GraphEdge, GraphNode, KnowledgeBase, KnowledgeGraph
from kt_ai.pipeline.understanding import SystemView


def _service_node_id(name: str) -> str:
    return f"service:{name}"


def build_knowledge_graph(knowledge: KnowledgeBase, system_view: SystemView) -> KnowledgeGraph:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    edge_lookup = {
        (str(item.get("source", "")), str(item.get("target", ""))): item
        for item in system_view.service_dependency_details
    }

    nodes.append(
        GraphNode(
            node_id=f"repo:{knowledge.repository.local_path.name}",
            node_type="Repository",
            attributes={"source": knowledge.repository.source},
        )
    )

    for service_name, details in sorted(system_view.services.items()):
        nodes.append(
            GraphNode(
                node_id=_service_node_id(service_name),
                node_type="Service",
                attributes={
                    "runtime": details.get("runtime", []),
                    "apis": details.get("apis", []),
                    "infra": details.get("infra", []),
                    "deployable": str(details.get("deployable", "no")),
                    "deployable_source": str(details.get("deployable_source", "unknown")),
                    "confidence": str(details.get("confidence", "0.00")),
                    "evidence_sources": details.get("evidence_sources", []),
                },
            )
        )

        edges.append(
            GraphEdge(
                source_id=f"repo:{knowledge.repository.local_path.name}",
                relationship="CONTAINS",
                target_id=_service_node_id(service_name),
            )
        )

    for source, target in system_view.service_dependencies:
        detail = edge_lookup.get((source, target), {})
        edges.append(
            GraphEdge(
                source_id=_service_node_id(source),
                relationship="CALLS",
                target_id=_service_node_id(target),
                attributes={
                    "confidence": float(detail.get("confidence", 0.6)),
                    "evidence": str(detail.get("evidence", "heuristic inference")),
                },
            )
        )

    for database in sorted(knowledge.databases):
        db_id = f"database:{database}"
        nodes.append(GraphNode(node_id=db_id, node_type="Database", attributes={}))
        for service_name, service in knowledge.services.items():
            if database in service.dependencies:
                edges.append(
                    GraphEdge(source_id=_service_node_id(service_name), relationship="USES", target_id=db_id)
                )

    for queue in sorted(knowledge.queues):
        queue_id = f"queue:{queue}"
        nodes.append(GraphNode(node_id=queue_id, node_type="Queue", attributes={}))
        for service_name, service in knowledge.services.items():
            if queue in service.dependencies:
                edges.append(
                    GraphEdge(source_id=_service_node_id(service_name), relationship="USES", target_id=queue_id)
                )

    for ci in sorted(knowledge.ci_pipelines):
        ci_id = f"pipeline:{ci}"
        nodes.append(GraphNode(node_id=ci_id, node_type="CIPipeline", attributes={}))
        edges.append(
            GraphEdge(
                source_id=f"repo:{knowledge.repository.local_path.name}",
                relationship="BUILT_BY",
                target_id=ci_id,
            )
        )

    return KnowledgeGraph(nodes=nodes, edges=edges)
