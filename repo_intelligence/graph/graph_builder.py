from __future__ import annotations

import networkx as nx

from repo_intelligence.models.system_model import SystemModel


def build_graph(system_model: SystemModel) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()

    graph.add_node(
        f"repo:{system_model.repository.local_path}",
        node_type="Repository",
        source=system_model.repository.source,
    )

    for service in system_model.services:
        service_id = f"service:{service.name}"
        graph.add_node(
            service_id,
            node_type="Service",
            name=service.name,
            path=service.path,
            runtime=service.runtime,
            confidence=service.confidence,
            source=service.source,
            component_type=service.component_type,
            classification_confidence=service.classification_confidence,
            classification_reason=service.classification_reason,
        )
        graph.add_edge(f"repo:{system_model.repository.local_path}", service_id, relationship="CONTAINS")

        for api in service.apis:
            api_id = f"api:{service.name}:{api}"
            graph.add_node(api_id, node_type="API", name=api)
            graph.add_edge(service_id, api_id, relationship="EXPOSES")

        for db in service.databases:
            db_id = f"database:{db}"
            graph.add_node(db_id, node_type="Database", name=db)
            graph.add_edge(service_id, db_id, relationship="USES")

    for dep in system_model.dependencies:
        source_id = f"service:{dep.source_service}"
        target_is_service = any(s.name == dep.target for s in system_model.services)
        if target_is_service:
            target_id = f"service:{dep.target}"
        elif dep.type == "DATABASE":
            target_id = f"database:{dep.target}"
            graph.add_node(target_id, node_type="Database", name=dep.target)
        elif dep.type == "QUEUE":
            target_id = f"queue:{dep.target}"
            graph.add_node(target_id, node_type="Queue", name=dep.target)
        else:
            target_id = f"component:{dep.target}"
            graph.add_node(target_id, node_type="Component", name=dep.target)

        relationship = "CALLS" if dep.type == "HTTP" else "USES"
        if dep.type == "QUEUE":
            relationship = "PUBLISHES"
        graph.add_edge(
            source_id,
            target_id,
            relationship=relationship,
            dep_type=dep.type,
            confidence=dep.confidence,
            evidence=dep.evidence,
        )

    return graph


def graph_to_json(graph: nx.MultiDiGraph) -> dict[str, list[dict[str, object]]]:
    nodes: list[dict[str, object]] = []
    for node_id, attrs in graph.nodes(data=True):
        nodes.append({"id": node_id, "labels": [str(attrs.get("node_type", "Entity"))], "properties": dict(attrs)})

    relationships: list[dict[str, object]] = []
    for source, target, attrs in graph.edges(data=True):
        relationships.append(
            {
                "start": source,
                "end": target,
                "type": str(attrs.get("relationship", "RELATED")),
                "properties": {k: v for k, v in attrs.items() if k != "relationship"},
            }
        )

    return {"nodes": nodes, "relationships": relationships}
