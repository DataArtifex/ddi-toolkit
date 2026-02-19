import os
import sys
import time
import uuid

# Setup path
sys.path.append(os.path.join(os.getcwd(), "src"))

from dartfx.ddi.ddicdi import model_1_0_0 as model
from dartfx.ddi.ddicdi.assistants import CdiClassAssistant


def benchmark_uuid(n=10000):
    start = time.time()
    for _ in range(n):
        str(uuid.uuid4())
    end = time.time()
    print(f"UUID v4 Generation (N={n}): {end - start:.4f}s")

    start = time.time()
    for _ in range(n):
        CdiClassAssistant.create(model.InstanceVariable, id_prefix="static")
    end = time.time()
    print(f"Assistant.create() with static prefix (N={n}): {end - start:.4f}s")


if __name__ == "__main__":
    benchmark_uuid(10000)
