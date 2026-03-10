import pandas as pd
import matplotlib.pyplot as plt

# carregar dataset
df = pd.read_csv("data/dados_projeto.csv")

# converter datas automaticamente
df["data"] = pd.to_datetime(df["data"], format="mixed")

# ordenar cronologicamente
df = df.sort_values("data")

# label versão + ano
df["label"] = df["versao"] + " (" + df["data"].dt.year.astype(str) + ")"

# -------------------------
# 1 LOC total
# -------------------------
plt.figure()
plt.plot(df["label"], df["loc"], marker="o")
plt.title("Evolução do tamanho do código (LOC)")
plt.xlabel("Versão")
plt.ylabel("LOC")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("graficos/01_loc_total.png")
plt.close()

# -------------------------
# 2 Estrutura do projeto
# -------------------------
plt.figure()
plt.plot(df["label"], df["arquivos"], marker="o", label="Arquivos")
plt.plot(df["label"], df["diretorio"], marker="o", label="Diretórios")
plt.title("Estrutura do projeto")
plt.xlabel("Versão")
plt.ylabel("Quantidade")
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("graficos/02_estrutura.png")
plt.close()

# -------------------------
# 3 Atividade
# -------------------------
plt.figure()
plt.plot(df["label"], df["commits"], marker="o", label="Commits")
plt.plot(df["label"], df["contribuidores"], marker="o", label="Contribuidores")
plt.title("Atividade do projeto")
plt.xlabel("Versão")
plt.ylabel("Quantidade")
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("graficos/03_atividade.png")
plt.close()

# -------------------------
# 4 Linguagens
# -------------------------
plt.figure()

plt.plot(df["label"], df["loc_js"], marker="o", label="JavaScript")
plt.plot(df["label"], df["loc_ts"], marker="o", label="TypeScript")
plt.plot(df["label"], df["loc_html"], marker="o", label="HTML")
plt.plot(df["label"], df["loc_css"], marker="o", label="CSS")
plt.plot(df["label"], df["loc_php"], marker="o", label="PHP")

plt.title("Evolução das linguagens")
plt.xlabel("Versão")
plt.ylabel("LOC")
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("graficos/04_linguagens.png")
plt.close()

# -------------------------
# 5 Crescimento de LOC
# -------------------------
df["crescimento_loc"] = df["loc"].diff()

plt.figure()
plt.bar(df["label"], df["crescimento_loc"])
plt.title("Crescimento de LOC por versão")
plt.xlabel("Versão")
plt.ylabel("LOC adicionados")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("graficos/05_crescimento_loc.png")
plt.close()

# -------------------------
# 6 Percentual de linguagens
# -------------------------
df["total_linguagens"] = (
    df["loc_js"] +
    df["loc_ts"] +
    df["loc_html"] +
    df["loc_css"] +
    df["loc_php"]
)

df["js_pct"] = df["loc_js"] / df["total_linguagens"] * 100
df["ts_pct"] = df["loc_ts"] / df["total_linguagens"] * 100

plt.figure()
plt.plot(df["label"], df["js_pct"], marker="o", label="JS %")
plt.plot(df["label"], df["ts_pct"], marker="o", label="TS %")

plt.title("Percentual de JavaScript vs TypeScript")
plt.xlabel("Versão")
plt.ylabel("% do código")
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("graficos/06_percentual_js_ts.png")
plt.close()

# -------------------------
# 7 LOC por contribuidor
# -------------------------
df["loc_por_contribuidor"] = df["loc"] / df["contribuidores"]

plt.figure()
plt.plot(df["label"], df["loc_por_contribuidor"], marker="o")
plt.title("LOC por contribuidor")
plt.xlabel("Versão")
plt.ylabel("LOC / contribuidor")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("graficos/07_loc_por_contribuidor.png")
plt.close()

# -------------------------
# 8 Commits por contribuidor
# -------------------------
df["commits_por_contribuidor"] = df["commits"] / df["contribuidores"]

plt.figure()
plt.plot(df["label"], df["commits_por_contribuidor"], marker="o")
plt.title("Commits por contribuidor")
plt.xlabel("Versão")
plt.ylabel("Commits / contribuidor")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("graficos/08_commits_por_contribuidor.png")
plt.close()

# -------------------------
# 9 Migração JS -> TS
# -------------------------
plt.figure()

plt.stackplot(
    df["label"],
    df["loc_js"],
    df["loc_ts"],
    labels=["JavaScript", "TypeScript"]
)

plt.title("Migração tecnológica JS → TS")
plt.xlabel("Versão")
plt.ylabel("LOC")
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("graficos/09_migracao_js_ts.png")
plt.close()

# -------------------------
# 10 Taxa de crescimento anual de LOC
# -------------------------

df["taxa_crescimento"] = df["loc"].pct_change() * 100

plt.figure()
plt.plot(df["label"], df["taxa_crescimento"], marker="o")

plt.title("Taxa de crescimento do código por versão")
plt.xlabel("Versão")
plt.ylabel("Crescimento (%)")

plt.xticks(rotation=45)
plt.tight_layout()

plt.savefig("graficos/10_taxa_crescimento.png")
plt.close()

print("Todos os gráficos foram gerados com sucesso.")