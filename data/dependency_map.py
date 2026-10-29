
"""
SignalSage AIOps - Service Dependency Map

An illustrative dependency graph for our synthetic demo.
The relationships must be validated against the actual
service dependency map before production use.
"""

from collections import deque


# Format: service -> services it directly depends on
SERVICE_DEPENDENCIES = {
    "orders-api": ["postgres-primary", "redis-cache"],
    "billing-api": ["postgres-primary", "payment-gateway"],
    "checkout-api": ["orders-api", "payment-gateway", "redis-cache"],
    "inventory-api": ["postgres-primary"],
    "catalog-api": ["postgres-primary", "redis-cache"],
    "session-api": ["redis-cache"],
    "auth-api": ["postgres-primary", "redis-cache"],
    "search-api": ["postgres-primary", "redis-cache"],
    "email-worker": ["orders-api"],
    "postgres-primary": [],
    "redis-cache": [],
    "payment-gateway": [],
}


def get_dependencies(service):
    """Return the direct dependencies of a service."""
    return SERVICE_DEPENDENCIES.get(service, [])


def get_dependents(service):
    """Return services that directly depend on this service."""
    return [
        name
        for name, dependencies in SERVICE_DEPENDENCIES.items()
        if service in dependencies
    ]


def get_upstream_dependencies(service):
    """Find all transitive dependencies of a service."""
    visited = set()
    queue = deque(get_dependencies(service))

    while queue:
        dependency = queue.popleft()

        if dependency in visited:
            continue

        visited.add(dependency)
        queue.extend(get_dependencies(dependency))

    return sorted(visited)


def explain_dependency(service, possible_root_cause):
    """
    Explain whether a proposed root cause is a dependency
    of the affected service.
    """
    if service == possible_root_cause:
        return f"{service} is the service reporting the alert."

    dependencies = get_upstream_dependencies(service)

    if possible_root_cause in dependencies:
        return (
            f"{service} depends directly or indirectly on "
            f"{possible_root_cause}; this is a plausible dependency "
            "relationship, not proof of causation."
        )

    return (
        f"No dependency path was found from {service} to "
        f"{possible_root_cause} in the configured demo map."
    )


if __name__ == "__main__":
    print("SignalSage AIOps - Dependency Map")
    print("=" * 40)

    service = "checkout-api"

    print(f"\nDirect dependencies of {service}:")
    print(get_dependencies(service))

    print(f"\nAll upstream dependencies of {service}:")
    print(get_upstream_dependencies(service))

    print("\nServices depending on postgres-primary:")
    print(get_dependents("postgres-primary"))

    print("\nDependency explanation:")
    print(explain_dependency("checkout-api", "postgres-primary"))