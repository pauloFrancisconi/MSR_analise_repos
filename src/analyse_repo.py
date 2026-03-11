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
    "6.0.0",   
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


# ─── LANGUAGE CONFIGS ────────────────────────────────────────────────────────
LANGUAGE_CONFIGS = {
    "js_ts": {
        "extensions": (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"),
        "import_patterns": [
            r"""(?:import\s+(?:[^'"]+\s+from\s+)?['"]([^'"]+)['"])""",
            r"""(?:require\(\s*['"]([^'"]+)['"]\s*\))""",
            r"""(?:import\(\s*['"]([^'"]+)['"]\s*\))""",
        ],
        # Imports relativos começam com . ou ..
        "is_internal": lambda i: bool(re.match(r"^\.", i)),
    },
    "python": {
        "extensions": (".py",),
        "import_patterns": [
            r"""^from\s+(\.+[\w.]*)\s+import""",   # from .module import ...
            r"""^import\s+(\.+[\w.]*)""",            # import .module (raro, mas válido)
        ],
        "is_internal": lambda i: i.startswith("."),
    },
    "php": {
        "extensions": (".php",),
        "import_patterns": [
            r"""(?:require|include|require_once|include_once)\s*\(?['"]([^'"]+)['"]\)?""",
        ],
        "is_internal": lambda i: not i.startswith("http") and "/" in i,
    },
    "java": {
        "extensions": (".java",),
        "import_patterns": [
            r"""^import\s+([\w.]+);""",
        ],
        # Heurística: imports do próprio projeto (ajuste o prefixo conforme necessário)
        "is_internal": lambda i: not any(
            i.startswith(pkg)
            for pkg in ("java.", "javax.", "org.springframework.", "com.google.", "org.apache.")
        ),
    },
    "ruby": {
        "extensions": (".rb",),
        "import_patterns": [
            r"""(?:require_relative\s+['"]([^'"]+)['"])""",
            r"""(?:require\s+['"](\./[^'"]+)['"])""",  # require com caminho relativo
        ],
        "is_internal": lambda i: i.startswith(".") or not i.startswith("/"),
    },
}


def _detect_language(filepath: str):
    """Retorna a config da linguagem com base na extensão do arquivo."""
    for lang, cfg in LANGUAGE_CONFIGS.items():
        if filepath.endswith(cfg["extensions"]):
            return lang, cfg
    return None, None


def _extract_imports(content: str, patterns: list[str], is_internal) -> list[str]:
    """Extrai imports internos de um arquivo dado os padrões da linguagem."""
    found = []
    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        # re.findall retorna strings ou tuplas dependendo dos grupos
        for m in matches:
            token = m if isinstance(m, str) else next((x for x in m if x), "")
            if token and is_internal(token):
                found.append(token)
    return found


# ─── DEPENDENCY METRICS (multi-linguagem) ────────────────────────────────────
def dependency_metrics(files):
    """
    Analisa imports internos de JS/TS, Python, PHP, Java e Ruby.
    Retorna (fanout_avg, fanout_max, total_imports).
    """
    fanouts = []
    total_imports = 0

    for f in files:
        _, cfg = _detect_language(f)
        if cfg is None:
            continue

        try:
            content = open(f, errors="ignore").read()
        except OSError as e:
            print(f"Warning (dependency_metrics): {e}")
            continue

        imports = _extract_imports(content, cfg["import_patterns"], cfg["is_internal"])
        fanouts.append(len(imports))
        total_imports += len(imports)

    if not fanouts:
        return 0, 0, 0

    return sum(fanouts) / len(fanouts), max(fanouts), total_imports


# ─── DEPENDENCY GRAPH (multi-linguagem) ──────────────────────────────────────
def dependency_graph(files):
    """
    Constrói grafo dirigido de dependências internas para todas as linguagens
    suportadas. Nós normalizados como caminhos relativos ao REPO_PATH.
    """
    G = nx.DiGraph()

    for f in files:
        _, cfg = _detect_language(f)
        if cfg is None:
            continue

        try:
            content = open(f, errors="ignore").read()
        except OSError as e:
            print(f"Warning (dependency_graph): {e}")
            continue

        imports = _extract_imports(content, cfg["import_patterns"], cfg["is_internal"])
        src_node = os.path.relpath(f, REPO_PATH)

        for dep in imports:
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