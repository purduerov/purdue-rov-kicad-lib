import time
import os

large_file = "large_test.kicad_sym"
with open("Symbols/rov_connectors.kicad_sym", "r") as src, open(large_file, "w") as dst:
    content = src.read()
    for _ in range(20000):
        dst.write(content)

print(f"Created {large_file} with size {os.path.getsize(large_file)/1024/1024:.2f} MB")

start = time.time()
os.system(f"python3 scripts/linter_validator.py {large_file} > /dev/null 2>&1")
end = time.time()

print(f"Time taken: {end-start:.4f} seconds")

os.remove(large_file)
