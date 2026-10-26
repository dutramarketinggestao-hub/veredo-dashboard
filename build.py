"""Gera index.html a partir das respostas brutas do Meta Ads salvas em raw/.

Uso: python3 build.py AAAA-MM-DD   (data da atualização; o período termina no dia anterior)

Arquivos esperados (cada um é o array `ad_entities` devolvido pelo Meta Ads, sem alterações):
  raw/semanal.json            campanhas de leads, 90 dias, time_increment 7
  raw/diario.json             campanhas de leads, 14 dias, time_increment 1
  raw/<P>/campanhas.json      todas as campanhas do período P
  raw/<P>/estados.json        conta inteira, breakdown region
  raw/<P>/posicionamentos.json campanhas de leads, breakdown publisher_platform + platform_position
  raw/<P>/idade.json          campanhas de leads, breakdown age + gender
  raw/<P>/anuncios.json       12 anúncios de leads com maior investimento
P = 7, 14, 30, 60, 90
"""
import json, sys, datetime, pathlib

ROOT = pathlib.Path(__file__).parent
P = [7, 14, 30, 60, 90]
AGES = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]


def load(path):
    t = json.loads((ROOT / "raw" / path).read_text(encoding="utf-8"))
    if isinstance(t, dict) and "ad_entities" in t:
        t = t["ad_entities"]
    if isinstance(t, str):
        t = json.loads(t)
    return t


def num(v):
    if isinstance(v, dict):
        v = v.get("value")
    if v in (None, ""):
        return 0.0
    try:
        return float(str(v).replace("%", "").replace(",", "."))
    except ValueError:
        return 0.0


def div(a, b):
    return a / b if b else None


def prod_of(name):
    return "C" if "CONT" in (name or "").upper() else "A"


POS = {"feed": "Feed", "instagram_reels": "Reels", "facebook_reels": "Reels", "instagram_stories": "Stories",
       "facebook_stories": "Stories", "instagram_explore_grid_home": "Explorar", "instagram_lead_gen_multi_submit": "Formulário múltiplo",
       "marketplace": "Marketplace", "search": "Busca", "instagram_search": "Busca", "instream_video": "In-stream",
       "facebook_notification": "Notificações", "an_classic": "", "unknown": "Não informado"}
PLAT = {"instagram": "Instagram", "facebook": "Facebook", "audience_network": "Audience Network", "unknown": ""}
UF = {"Federal District": "Distrito Federal"}


def fmt_ad(n):
    n = (n or "").upper()
    return "Vídeo" if n.startswith("VIDEO") else "Dinâmico" if n.startswith("DIN") else "Artes" if n.startswith("ARTES") else "Imagem"


def build(hoje):
    ate = hoje - datetime.timedelta(days=1)
    semanal, diario = load("semanal.json"), load("diario.json")

    def series(rows):
        m = {}
        for r in rows:
            o = m.setdefault(r["date_start"], dict(x=r["date_start"], investimento=0, leads=0, impressoes=0, cliques=0))
            o["investimento"] += num(r.get("amount_spent")); o["leads"] += num(r.get("lead"))
            o["impressoes"] += num(r.get("impressions")); o["cliques"] += num(r.get("link_click"))
        out = sorted(m.values(), key=lambda o: o["x"])
        for o in out:
            o["cpl"] = div(o["investimento"], o["leads"]); o["conv"] = div(o["leads"], o["cliques"])
        return out

    weeks, days = series(semanal), series(diario)
    out = {"atualizado": hoje.isoformat(), "periodos": {}}
    for p in P:
        de = ate - datetime.timedelta(days=p - 1)
        cs = load(f"{p}/campanhas.json")
        lc = [c for c in cs if c.get("objective") == "OUTCOME_LEADS"]
        s = lambda rows, k: sum(num(r.get(k)) for r in rows)
        inv, invL, L, I, K = s(cs, "amount_spent"), s(lc, "amount_spent"), s(lc, "lead"), s(lc, "impressions"), s(lc, "link_click")
        kpi = dict(investimento=inv, investimento_leads=invL, leads=L, cpl=div(invL, L), cliques=K, conv=div(L, K),
                   cpm=(div(invL, I) or 0) * 1000, ctr=div(K, I), impressoes=I)
        produtos = {}
        for pr in "AC":
            rows = [c for c in lc if prod_of(c.get("name")) == pr]
            a, b = s(rows, "amount_spent"), s(rows, "lead")
            produtos[pr] = dict(investimento=a, leads=b, cpl=div(a, b))
        campanhas = [dict(nome=c.get("name"), tipo="Leads" if c.get("objective") == "OUTCOME_LEADS" else "Engajamento",
                          status=c.get("effective_status"), investimento=num(c.get("amount_spent")), leads=num(c.get("lead")) or None,
                          cpl=div(num(c.get("amount_spent")), num(c.get("lead"))), impressoes=num(c.get("impressions")),
                          frequencia=num(c.get("frequency")), cliques=num(c.get("link_click")),
                          ctr=div(num(c.get("link_click")), num(c.get("impressions")))) for c in cs if num(c.get("amount_spent")) > 0]
        campanhas.sort(key=lambda o: -o["investimento"])
        serie = days[-p:] if p <= 14 else [w for w in weeks if w["x"] >= (de - datetime.timedelta(days=6)).isoformat()]

        pos_out, ida_out, gen_out = {}, {}, {}
        prow = load(f"{p}/posicionamentos.json"); irow = load(f"{p}/idade.json")
        for pr in "TAC":
            m = {}
            for r in prow:
                if pr != "T" and prod_of(r.get("name")) != pr:
                    continue
                k = (PLAT.get(r.get("publisher_platform"), r.get("publisher_platform")) + " " + POS.get(r.get("platform_position"), r.get("platform_position"))).strip() or "Outros"
                o = m.setdefault(k, dict(posicionamento=k, investimento=0, leads=0, impressoes=0, cliques=0))
                o["investimento"] += num(r.get("amount_spent")); o["leads"] += num(r.get("lead"))
                o["impressoes"] += num(r.get("impressions")); o["cliques"] += num(r.get("link_click"))
            tl = sum(o["leads"] for o in m.values())
            rows = []
            for o in m.values():
                if o["investimento"] < 1 and o["leads"] == 0:
                    continue
                o.update(cpl=div(o["investimento"], o["leads"]), ctr=div(o["cliques"], o["impressoes"]), part=div(o["leads"], tl))
                rows.append(o)
            pos_out[pr] = sorted(rows, key=lambda o: -o["investimento"])

            am = {a: dict(faixa=a, investimento=0, leads=0, inv_h=0, leads_h=0, inv_m=0, leads_m=0) for a in AGES}
            g = {"male": dict(genero="Homens", investimento=0, leads=0), "female": dict(genero="Mulheres", investimento=0, leads=0)}
            for r in irow:
                if pr != "T" and prod_of(r.get("name")) != pr:
                    continue
                sp, ld, gd = num(r.get("amount_spent")), num(r.get("lead")), r.get("gender")
                if r.get("age") in am:
                    o = am[r["age"]]; o["investimento"] += sp; o["leads"] += ld
                    if gd == "male": o["inv_h"] += sp; o["leads_h"] += ld
                    if gd == "female": o["inv_m"] += sp; o["leads_m"] += ld
                if gd in g:
                    g[gd]["investimento"] += sp; g[gd]["leads"] += ld
            for o in am.values():
                o.update(cpl=div(o["investimento"], o["leads"]), cpl_h=div(o["inv_h"], o["leads_h"]), cpl_m=div(o["inv_m"], o["leads_m"]))
            tg = sum(o["leads"] for o in g.values())
            for o in g.values():
                o.update(cpl=div(o["investimento"], o["leads"]), part=div(o["leads"], tg))
            ida_out[pr] = list(am.values()); gen_out[pr] = list(g.values())

        er = [r for r in load(f"{p}/estados.json") if r.get("region") != "Unknown"]
        tot = sum(num(r.get("amount_spent")) for r in er)
        estados = []
        for r in er:
            sp, im, ck = num(r.get("amount_spent")), num(r.get("impressions")), num(r.get("link_click"))
            if sp < 0.5:
                continue
            nome = UF.get(r["region"], r["region"].replace(" (state)", ""))
            estados.append(dict(estado=nome, investimento=sp, part=div(sp, tot), impressoes=im, cliques=ck, ctr=div(ck, im),
                                custo_clique=div(sp, ck), cpm=(div(sp, im) or 0) * 1000))
        estados.sort(key=lambda o: -o["investimento"])

        anuncios = [dict(id=a.get("id"), nome=a.get("name"), campanha=a.get("campaign_name"), status=a.get("effective_status"),
                         investimento=num(a.get("amount_spent")), leads=num(a.get("lead")) or None,
                         cpl=div(num(a.get("amount_spent")), num(a.get("lead"))), impressoes=num(a.get("impressions")),
                         cliques=num(a.get("link_click")), ctr=div(num(a.get("link_click")), num(a.get("impressions"))),
                         formato=fmt_ad(a.get("name"))) for a in load(f"{p}/anuncios.json")]

        out["periodos"][str(p)] = dict(de=de.isoformat(), ate=ate.isoformat(), passo="dia" if p <= 14 else "semana", kpi=kpi,
                                       produtos=produtos, campanhas=campanhas, serie=serie, posicionamentos=pos_out,
                                       idade=ida_out, genero=gen_out, estados=estados, anuncios=anuncios)

    def r(o):
        if isinstance(o, float):
            return round(o, 4) if abs(o) < 1 else round(o, 2)
        if isinstance(o, dict):
            return {k: r(v) for k, v in o.items()}
        if isinstance(o, list):
            return [r(v) for v in o]
        return o

    data = json.dumps(r(out), ensure_ascii=False, separators=(",", ":"))
    html = (ROOT / "template.html").read_text(encoding="utf-8").replace("__DATA__", data)
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    for p in P:
        k = out["periodos"][str(p)]["kpi"]
        print(f"{p:>2} dias: investimento {k['investimento']:.2f} · leads {k['leads']:.0f} · CPL {k['cpl'] or 0:.2f}")


if __name__ == "__main__":
    hoje = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today()
    build(hoje)
