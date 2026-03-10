import subprocess
import os
import re
import json
import csv
import statistics
import argparse
import networkx as nx


# ─── 1. ARGUMENTO DE CAMINHO DO REPOSITÓRIO ──────────────────────────────────

parser = argparse.ArgumentParser(description="MSR - Análise de repositório Git")
parser.add_argument(
    "--repo",
    type=str,
    default="./repo",
    help="Caminho para o repositório a ser analisado (default: ./repo)"
)
args = parser.parse_args()

REPO_PATH = args.repo

if not os.path.isdir(REPO_PATH):
    print(f"❌ Repositório não encontrado em: {REPO_PATH}")
    print("Use: uv run src/main.py --repo ./repo")
    exit(1)

print(f"📁 Analisando repositório em: {REPO_PATH}")


# ─── 2. VERSÕES ANALISADAS ───────────────────────────────────────────────────

tags = [
    "0.70.0",
    "1.0.0",
    "2.0.0",
    "3.0.0",
    "4.0.0",
    "5.0.0",
    "6.0.0",
    "7.0.0",
    "8.0.0",
]


# ─── 3. FUNÇÕES ──────────────────────────────────────────────────────────────

def checkout(tag):
    subprocess.run(
        ["git", "-C", REPO_PATH, "checkout", tag],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


def structure_metrics(repo):
    files = []
    dirs = []

    for root, d, f in os.walk(repo):
        dirs.extend(d)
        for file in f:
            files.append(os.path.join(root, file))

    return len(files), len(dirs), files


def depth_metrics(files):
    depths = []

    for f in files:
        depth = f.count(os.sep)
        depths.append(depth)

    if not depths:
        return 0, 0

    return (
        statistics.mean(depths),
        max(depths),
    )


def file_size_metrics(files):
    sizes = []

    for f in files:
        try:
            sizes.append(os.path.getsize(f))
        except OSError as e:
            print(f"Warning (file_size_metrics): {e}")

    if not sizes:
        return 0, 0

    return (
        sum(sizes) / len(sizes),
        max(sizes),
    )


def dependency_metrics(files):
    fanouts = []
    total_imports = 0

    for f in files:
        if not f.endswith(".py"):
            continue

        try:
            content = open(f, errors="ignore").read()
        except OSError as e:
            print(f"Warning (dependency_metrics): {e}")
            continue

        imports = re.findall(r"import (\w+)", content)
        fanouts.append(len(imports))
        total_imports += len(imports)

    if not fanouts:
        return 0, 0, 0

    return (
        sum(fanouts) / len(fanouts),
        max(fanouts),
        total_imports,
    )


def dependency_graph(files):
    G = nx.DiGraph()

    for f in files:
        if not f.endswith(".py"):
            continue

        try:
            content = open(f, errors="ignore").read()
        except OSError as e:
            print(f"Warning (dependency_graph): {e}")
            continue

        imports = re.findall(r"import (\w+)", content)

        for dep in imports:
            G.add_edge(f, dep)

    if G.number_of_nodes() == 0:
        return 0

    return nx.density(G)


def loc():
    result = subprocess.run(
        ["cloc", REPO_PATH, "--json"],
        capture_output=True,
        text=True,
    )

    try:
        data = json.loads(result.stdout)
        return data["SUM"]["code"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning (loc): {e}")
        return 0


def commits():
    result = subprocess.run(
        ["git", "-C", REPO_PATH, "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip())


def contributors():
    result = subprocess.run(
        ["git", "-C", REPO_PATH, "shortlog", "-sn"],
        capture_output=True,
        text=True,
    )
    return len(result.stdout.splitlines())


# ─── 4. LOOP PRINCIPAL ───────────────────────────────────────────────────────

rows = []

for tag in tags:

    print(f"Analyzing {tag}")

    checkout(tag)

    files_count, dirs_count, files = structure_metrics(REPO_PATH)

    avg_depth, max_depth = depth_metrics(files)

    avg_size, max_size = file_size_metrics(files)

    fan_avg, fan_max, total_deps = dependency_metrics(files)

    density = dependency_graph(files)

    loc_total = loc()

    commit_count = commits()

    contrib = contributors()

    rows.append([
        tag,
        loc_total,
        files_count,
        dirs_count,
        avg_depth,
        max_depth,
        avg_size,
        max_size,
        fan_avg,
        fan_max,
        total_deps,
        density,
        commit_count,
        contrib,
    ])


# ─── 5. EXPORTAÇÃO CSV ───────────────────────────────────────────────────────

with open("metrics.csv", "w", newline="") as f:

    writer = csv.writer(f)

    writer.writerow([
        "version",
        "loc",
        "files",
        "dirs",
        "avg_depth",
        "max_depth",
        "avg_file_size",
        "max_file_size",
        "fanout_avg",
        "fanout_max",
        "total_dependencies",
        "dependency_density",
        "commits",
        "contributors",
    ])

    writer.writerows(rows)

print("✅ metrics.csv gerado com sucesso!")