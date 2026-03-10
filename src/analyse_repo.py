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
    default="src/repo",
    help="Caminho para o repositório a ser analisado (default: ./repo)"
)
args = parser.parse_args()

REPO_PATH = args.repo

if not os.path.isdir(REPO_PATH):
    print(f"❌ Repositório não encontrado em: {REPO_PATH}")
    print("Use: uv run src/main.py --repo ./repo")
    exit(1)

print(f"📁 Analisando repositório em: {REPO_PATH}")

# ─── Diretórios a ignorar em todos os walks ──────────────────────────────────
IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".cache", "dist", "build", ".next", "coverage"}

# ─── 2. VERSÕES ANALISADAS ───────────────────────────────────────────────────
tags = [
    "0.70.0",
    "1.0.0",
    "2.0.0",
    "3.0.0",
    "4.0.0",
    "5.0.0",
    "6.0.1",   
    "7.0.0",
    "8.0.0",
]

# ─── 3. FUNÇÕES ──────────────────────────────────────────────────────────────
def checkout(tag):
    try:
        subprocess.run(
            ["git", "-C", REPO_PATH, "checkout", tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError:
        print(f"⚠️  Não foi possível fazer checkout da tag {tag}. Pulando...")
        return False
    return True


def structure_metrics(repo):
    """
    FIX: Filtra .git/, node_modules/ e outros diretórios irrelevantes
    para que files/dirs reflitam apenas o código-fonte real do projeto.
    """
    files = []
    dirs = []
    for root, d, f in os.walk(repo):
        # Poda in-place: os.walk não vai descer nesses diretórios
        d[:] = [x for x in d if x not in IGNORED_DIRS]
        dirs.extend(d)
        for file in f:
            files.append(os.path.join(root, file))
    return len(files), len(dirs), files


def depth_metrics(files):
    """
    FIX: Calcula profundidade relativa ao REPO_PATH, não absoluta,
    para que o valor não varie com o local de instalação.
    """
    depths = []
    base_depth = REPO_PATH.rstrip(os.sep).count(os.sep) + 1
    for f in files:
        depths.append(f.count(os.sep) - base_depth)
    if not depths:
        return 0, 0
    return statistics.mean(depths), max(depths)


def file_size_metrics(files):
    sizes = []
    for f in files:
        try:
            sizes.append(os.path.getsize(f))
        except OSError as e:
            print(f"Warning (file_size_metrics): {e}")
    if not sizes:
        return 0, 0
    return sum(sizes) / len(sizes), max(sizes)


# ─── DEPENDENCY METRICS PARA JS/TS ──────────────────────────────────────────
def dependency_metrics(files):
    """
    FIX: Só analisa arquivos .js/.ts que já foram filtrados (sem node_modules),
    garantindo que fanout_avg reflita o código-fonte real.
    """
    fanouts = []
    total_imports = 0

    for f in files:
        if not f.endswith((".js", ".ts")):
            continue

        try:
            content = open(f, errors="ignore").read()
        except OSError as e:
            print(f"Warning (dependency_metrics): {e}")
            continue

        imports = re.findall(
            r"""(?:import\s+(?:[^'"]+\s+from\s+)?['"]([^'"]+)['"])|
                (?:require\(\s*['"]([^'"]+)['"]\s*\))|
                (?:import\(\s*['"]([^'"]+)['"]\s*\))""",
            content,
            re.MULTILINE | re.VERBOSE,
        )

        # Considera apenas imports relativos (internos ao projeto)
        flat_imports = [
            i for t in imports for i in t if i and not re.match(r"^[a-z@]", i)
        ]

        fanouts.append(len(flat_imports))
        total_imports += len(flat_imports)

    if not fanouts:
        return 0, 0, 0

    return sum(fanouts) / len(fanouts), max(fanouts), total_imports


# ─── DEPENDENCY GRAPH PARA JS/TS ────────────────────────────────────────────
def dependency_graph(files):
    """
    FIX: Com node_modules fora do walk, o grafo agora tem apenas nós do
    projeto real — density deixa de ser ~0 e passa a ser interpretável.
    Normaliza os nós para caminhos relativos ao repo para evitar
    nós duplicados por diferença de prefixo absoluto.
    """
    G = nx.DiGraph()

    for f in files:
        if not f.endswith((".js", ".ts")):
            continue

        try:
            content = open(f, errors="ignore").read()
        except OSError as e:
            print(f"Warning (dependency_graph): {e}")
            continue

        imports = re.findall(
            r"""(?:import\s+(?:[^'"]+\s+from\s+)?['"]([^'"]+)['"])|
                (?:require\(\s*['"]([^'"]+)['"]\s*\))|
                (?:import\(\s*['"]([^'"]+)['"]\s*\))""",
            content,
            re.MULTILINE | re.VERBOSE,
        )

        flat_imports = [
            i for t in imports for i in t if i and not re.match(r"^[a-z@]", i)
        ]

        # Nó fonte normalizado (relativo ao repo)
        src_node = os.path.relpath(f, REPO_PATH)

        for dep in flat_imports:
            dep_abs  = os.path.normpath(os.path.join(os.path.dirname(f), dep))
            dep_node = os.path.relpath(dep_abs, REPO_PATH)
            G.add_edge(src_node, dep_node)

    if G.number_of_nodes() == 0:
        return 0

    return nx.density(G)


# ─── Outras métricas ─────────────────────────────────────────────────────────
def loc():
    result = subprocess.run(
        ["cloc", REPO_PATH, "--json", "--exclude-dir=" + ",".join(IGNORED_DIRS)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    try:
        if result.stdout:
            data = json.loads(result.stdout)
            return data["SUM"]["code"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning (loc): {e}")
    return 0


def commits_up_to_tag(tag):
    """
    FIX: Conta commits até a tag especificada explicitamente,
    tornando o valor determinístico independente do HEAD atual.
    Nota: valor cumulativo desde o início do repositório.
    """
    result = subprocess.run(
        ["git", "-C", REPO_PATH, "rev-list", "--count", tag],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if not result.stdout:
        return 0
    return int(result.stdout.strip())


def contributors_up_to_tag(tag):
    """
    FIX: Lista apenas os autores que contribuíram até a tag especificada.
    Nota: valor cumulativo desde o início do repositório.
    """
    result = subprocess.run(
        ["git", "-C", REPO_PATH, "shortlog", "-sn", tag],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if not result.stdout:
        return 0
    return len(result.stdout.splitlines())


# ─── 4. LOOP PRINCIPAL ───────────────────────────────────────────────────────
rows = []

for tag in tags:
    print(f"Analyzing {tag}...")
    if not checkout(tag):
        continue

    files_count, dirs_count, files = structure_metrics(REPO_PATH)
    avg_depth, max_depth           = depth_metrics(files)
    avg_size, max_size             = file_size_metrics(files)
    fan_avg, fan_max, total_deps   = dependency_metrics(files)
    density                        = dependency_graph(files)
    loc_total                      = loc()
    commit_count                   = commits_up_to_tag(tag)   
    contrib                        = contributors_up_to_tag(tag)  

    rows.append([
        tag, loc_total, files_count, dirs_count,
        round(avg_depth, 4), max_depth,
        round(avg_size, 2), max_size,
        round(fan_avg, 4), fan_max, total_deps,
        round(density, 8),
        commit_count, contrib
    ])

# ─── 5. EXPORTAÇÃO CSV ───────────────────────────────────────────────────────
with open("metrics.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "version", "loc", "files", "dirs",
        "avg_depth", "max_depth",
        "avg_file_size", "max_file_size",
        "fanout_avg", "fanout_max", "total_dependencies",
        "dependency_density",
        "commits_cumulative", "contributors_cumulative" 
    ])
    writer.writerows(rows)

print("✅ metrics.csv gerado com sucesso!")