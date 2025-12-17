## Chart templates (`chartTemplateId`)

Это директория для хранения определений шаблонов графиков, на которые ссылается поле `chartTemplateId` в:
- `flow_run.steps[stepId].inputs.requests[*].chartTemplateId`
- `ChartsOutputsManifest.requested[*].chartTemplateId`
- `ChartsOutputsManifest.items[*].chartTemplateId`

### Где лежат темплейты

- Каждый шаблон — отдельный файл в этой директории.
- Рекомендуемый формат:
  - **один файл на один `chartTemplateId`**;
  - имя файла совпадает с `chartTemplateId` + `.json`, например:
    - `ctpl_default_v1.json`
    - `ctpl_breakout_v1.json`
    - `ctpl_trend_follow_v1.json`
  - внутри файла — JSON-объект с конфигурацией TradingView / Chart-IMG Advanced Chart (API v2).

### Содержимое файла-шаблона (черновик)

Минимально шаблон может содержать:

- метаданные:
  - `id`: строка, совпадает с именем файла без `.json` (например, `ctpl_default_v1`);
  - `description`: человекочитаемое описание шаблона;
- конфигурацию для Chart-IMG API v2 Advanced Chart:
  - `request`: JSON-объект с полями тела запроса к `POST /v2/tradingview/advanced-chart`  
    (см. локальную документацию `chart-img-docs/API Documentation.htm`, раздел **TradingView Snapshot v2 / Advanced Chart**).

Пример скелета (без привязки к конкретному символу/таймфрейму):

```json
{
  "id": "ctpl_example_v1",
  "description": "Example chart template (dark, 1h baseline with volume + MACD).",
  "request": {
    "theme": "dark",
    "interval": "1h",
    "style": "baseline",
    "studies": [
      { "name": "Volume", "forceOverlay": true },
      { "name": "MACD" }
    ],
    "override": {
      "showStudyLastValue": false
    }
  }
}
```

### Динамические поля (symbol, timeframe)

- Поля `symbol`, `interval`, `timezone` и т.п. в реальном запросе к Chart-IMG будут формироваться воркером на основе:
  - `flow_run.scope.symbol`
  - `flow_run.steps[stepId].timeframe`
  - глобальной конфигурации (например, дефолтный `timezone`)
- Шаблон здесь описывает **форму и оформление графика** (style, theme, studies, overrides, drawings и т.д.), а не конкретный тикер.

Конкретная семантика `chartTemplateId` (что строго входит в шаблон, как работает версионирование и совместимость) описывается в отдельной спецификации и может эволюционировать. Эта директория служит “местом”, куда можно положить 5 (и более) темплейтов в виде JSON-файлов.


