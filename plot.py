import pandas as pd
import matplotlib.pyplot as plt

# ─── 1. Ler CSV gerado ───────────────────────────────────────────────────────
df = pd.read_csv("metrics.csv")

# ─── 2. Configurações básicas do Matplotlib ─────────────────────────────────
plt.style.use("seaborn-darkgrid")
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["font.size"] = 12

# ─── 3. Gráfico LOC vs Version ───────────────────────────────────────────────
plt.figure()
plt.plot(df["version"], df["loc"], marker="o", color="tab:blue", label="LOC")
plt.title("LOC por Versão")
plt.xlabel("Versão")
plt.ylabel("LOC (Linhas de Código)")
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig("plots/plot_loc.png")

# ─── 4. Número de arquivos e diretórios ─────────────────────────────────────
plt.figure()
plt.plot(df["version"], df["files"], marker="o", label="Arquivos")
plt.plot(df["version"], df["dirs"], marker="o", label="Diretórios")
plt.title("Evolução de Arquivos e Diretórios")
plt.xlabel("Versão")
plt.ylabel("Quantidade")
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig("plots/plot_files_dirs.png")

# ─── 5. Profundidade média e máxima ─────────────────────────────────────────
plt.figure()
plt.plot(df["version"], df["avg_depth"], marker="o", label="Profundidade Média")
plt.plot(df["version"], df["max_depth"], marker="o", label="Profundidade Máxima")
plt.title("Evolução da Profundidade de Pastas")
plt.xlabel("Versão")
plt.ylabel("Profundidade")
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig("plots/plot_depth.png")

# ─── 6. Fanout médio e máximo ───────────────────────────────────────────────
plt.figure()
plt.plot(df["version"], df["fanout_avg"], marker="o", label="Fanout Médio")
plt.plot(df["version"], df["fanout_max"], marker="o", label="Fanout Máximo")
plt.title("Evolução de Dependências (Fanout)")
plt.xlabel("Versão")
plt.ylabel("Número de Dependências")
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig("plots/plot_fanout.png")

# ─── 7. Densidade de dependências ───────────────────────────────────────────
plt.figure()
plt.plot(df["version"], df["dependency_density"], marker="o", color="tab:red", label="Densidade")
plt.title("Densidade do Grafo de Dependências")
plt.xlabel("Versão")
plt.ylabel("Densidade")
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig("plots/plot_density.png")

# ─── 8. Commits e Contributors ──────────────────────────────────────────────
plt.figure()
plt.plot(df["version"], df["commits"], marker="o", label="Commits")
plt.plot(df["version"], df["contributors"], marker="o", label="Contributors")
plt.title("Atividade do Projeto por Versão")
plt.xlabel("Versão")
plt.ylabel("Quantidade")
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig("plots/plot_activity.png")

print("Gráficos gerados e salvos em PNG!")
plt.show()