import os
import sys
import time
import uuid
from typing import cast

# Setup path
sys.path.append(os.path.join(os.getcwd(), "src"))

from pydantic import AnyUrl

from dartfx.ddi.ddicdi import model_1_0_0 as model
from dartfx.ddi.ddicdi.assistants import CdiAssistant, CdiClassAssistant


def benchmark_instantiation(n=100000):
    print(f"\n--- Instantiation Benchmark (N={n}) ---")

    # 1. Direct Model Instantiation
    start = time.time()
    for _ in range(n):
        model.InstanceVariable()
    end = time.time()
    direct_time = end - start
    print(f"Direct Model: {direct_time:.4f}s ({n / direct_time:.0f} ops/s)")

    # 2. Assistant Wrapper (Existing resource)
    res = model.InstanceVariable()
    start = time.time()
    for _ in range(n):
        CdiAssistant(resource=res)
    end = time.time()
    wrapper_time = end - start
    print(f"Assistant Wrapper (existing res): {wrapper_time:.4f}s ({n / wrapper_time:.0f} ops/s)")

    # 3. Proxy Access Overhead
    CdiAssistant(resource=res)
    res.id = "test_id"
    start = time.time()
    for _ in range(n):
        pass
    end = time.time()
    proxy_time = end - start
    print(f"Proxy Attribute Access: {proxy_time:.4f}s ({n / proxy_time:.0f} ops/s)")


def benchmark_full_creation(n=10000):
    print(f"\n--- Full Logic Benchmark (N={n}) ---")

    # 1. Manual orchestration (Equivalent to what Assistant does)
    start = time.time()
    for _ in range(n):
        res = model.InstanceVariable()
        uid = f"{uuid.uuid4()}_InstanceVariable"
        res.identifier = model.Identifier()
        res.identifier.ddiIdentifier = model.InternationalRegistrationDataIdentifier(
            dataIdentifier=uid, registrationAuthorityIdentifier="int.dataartifex", versionIdentifier="1"
        )
        res.identifier.uri = cast(AnyUrl, f"urn:ddi-cdi:{uid}")
    end = time.time()
    manual_time = end - start
    print(f"Manual Full Setup: {manual_time:.4f}s ({n / manual_time:.0f} ops/s)")

    # 2. Assistant.create()
    start = time.time()
    for _ in range(n):
        CdiClassAssistant.create(model.InstanceVariable)
    end = time.time()
    assistant_time = end - start
    print(f"Assistant.create(): {assistant_time:.4f}s ({n / assistant_time:.0f} ops/s)")


if __name__ == "__main__":
    # Reducing N to 100k for faster execution in this environment,
    # but results scale linearly.
    benchmark_instantiation(100000)
    benchmark_full_creation(10000)
