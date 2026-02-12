# DDI-CDI Assistant Performance Report

This report analyzes the performance overhead of using the DDI-CDI Assistant framework compared to direct Pydantic model instantiation.

## Overview

The DDI-CDI Assistant framework provides a high-level API for creating and manipulating DDI-CDI resources. While it introduces some overhead, the framework has been optimized to minimize this impact, particularly by removing dynamic field inspection during resource creation.

## Benchmark Results

Benchmarks were performed with **N=100,000** iterations for simple operations and **N=10,000** for full creation logic.

| Test Case | Ops / Second | Time per Object | Overhead vs Direct |
| :--- | :--- | :--- | :--- |
| **Direct Model Instantiation** | ~867,000 | **1.15µs** | Base (100%) |
| **Assistant Wrapping (Existing Res)** | ~1,490,000 | **0.67µs** | +0.67µs per wrap |
| **Proxy Attribute Access** | ~6,970,000 | **0.14µs** | Negligible |
| **Manual Full Setup** (Res + UUID + IDs)| ~106,000 | **9.41µs** | +8.26µs |
| **Assistant.create()** (Full Logic) | ~86,000 | **11.57µs** | +10.42µs |

---

## Bottleneck Analysis

The total creation time of **11.57µs** per object can be decomposed into the following primary factors:

### 1. Pydantic Nested Object Creation (~43%)
*   **Cost**: ~5.0µs per call.
*   **Description**: Setting a DDI identifier involves creating several nested "Value Objects" (e.g., `model.Identifier`, `model.InternationalString`).
*   **Impact**: This is the most significant bottleneck, stemming from Pydantic's validation and instantiation process for complex types.

### 2. Assistant Orchestration (~28%)
*   **Cost**: ~3.2µs per call.
*   **Description**:
    *   Creation of the `CdiClassAssistant` wrapper.
    *   Method proxying via `AssistantMethodDescriptor`.
    *   String formatting for URNs and UIDs.
*   **Impact**: Necessary for the convenience of the Assistant API; remains efficient relative to the underlying model logic.

### 3. UUID Generation (~19%)
*   **Cost**: ~2.23µs per call.
*   **Description**: Generation of `uuid.uuid4()` for unique identifiers.
*   **Impact**: Limits total creation speed to ~450k objects/sec even if all other logic were zero-cost.

### 4. Property Proxying (<2%)
*   **Cost**: ~0.14µs per access.
*   **Description**: Accessing model attributes through the assistant (e.g., `assistant.name`).
*   **Impact**: Extremely efficient; unlikely to ever be a bottleneck in data processing workflows.

---

## Recommendations for High-Scale Operations

For workflows involving millions of resources where absolute performance is critical:

1.  **Static ID Prefixes**: Provide a pre-calculated `id_prefix` to the `factory` or `create` method to skip the cost of UUID generation.
2.  **Batch Processing**: In highly specialized loops, consider direct model instantiation if the advanced features of the assistant (like automatic RDF graph binding or helper methods) are not required for every single object.
3.  **Generic Class Assistant**: Use `CdiClassAssistant` rather than specialized subclasses unless specific helper methods are required, as it minimizes the lookup chain.

## Conclusion

The DDI-CDI Assistant framework adds approximately **10µs** of overhead per resource creation. For the vast majority of use cases, this is an excellent trade-off for the significantly improved developer experience, automatic identifier management, and standardized RDF integration.
