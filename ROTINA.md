# Atualização diária do dashboard

Roteiro da tarefa agendada que atualiza `index.html` com os dados do Meta Ads da conta **Veredo01 (ID 910992611304428)**.

## Datas

- `HOJE` = data atual em America/Sao_Paulo. `ATE` = HOJE − 1 dia.
- Para cada período P em 7, 14, 30, 60, 90: `DE_P` = ATE − (P − 1) dias.
- `time_range` sempre no formato `{"since":"AAAA-MM-DD","until":"AAAA-MM-DD"}`.

## Chamadas (ferramenta `ads_get_ad_entities` do conector Meta Ads)

Em todas: `ad_account_id: "910992611304428"`, `advertiser_job: "report_measure_or_look_up"`, `reporting_purpose: ["other"]`, `include_additional_context: false`.

`LEADS` = `filtering: [{"field":"objective","operator":"IN","value":["OUTCOME_LEADS"]},{"field":"amount_spent","operator":"GREATER_THAN","value":["0"]}]`

| Arquivo | level | fields | outros parâmetros |
|---|---|---|---|
| `raw/semanal.json` | campaign | name, amount_spent, lead, impressions, link_click | LEADS, time_range DE_90→ATE, time_increment "7", limit 1000 |
| `raw/diario.json` | campaign | name, amount_spent, lead, impressions, link_click | LEADS, time_range DE_14→ATE, time_increment "1", limit 1000 |
| `raw/P/campanhas.json` | campaign | name, objective, effective_status, amount_spent, lead, impressions, frequency, link_click | filtering só amount_spent > 0, time_range DE_P→ATE |
| `raw/P/estados.json` | ad_account | amount_spent, impressions, link_click | breakdowns ["region"], time_range DE_P→ATE (sem filtering) |
| `raw/P/posicionamentos.json` | campaign | amount_spent, lead, impressions, link_click | LEADS, breakdowns ["publisher_platform","platform_position"], time_range DE_P→ATE, limit 1000 |
| `raw/P/idade.json` | campaign | amount_spent, lead | LEADS, breakdowns ["age","gender"], time_range DE_P→ATE, limit 1000 |
| `raw/P/anuncios.json` | ad | name, campaign_name, effective_status, amount_spent, lead, impressions, link_click | filtering objective IN OUTCOME_LEADS e amount_spent > 3, sort "amount_spent_descending", limit 12, time_range DE_P→ATE |

Salve em cada arquivo **exatamente** o valor de `ad_entities` da resposta (o texto JSON do array), sem editar números. Ignore `pagination`.

## Publicar

```bash
python3 build.py HOJE          # gera index.html e imprime um resumo por período
git add -A && git commit -m "Atualiza dados até ATE" && git push origin main
```

Se alguma chamada falhar, não publique: deixe o `index.html` anterior no ar.
