# Именование изображений графиков (prototype)

Цель: чтобы по **одному пути PNG в GCS** было понятно:

- когда сгенерировали
- по какому символу
- какой таймфрейм
- какой шаблон
- какой “вид” изображения (kind)

## Директория

PNG для каждого шаблона записываются в директорию:

`runs/<runId>/charts/<timeframe>/<chartTemplateId>/`

> Примечание: `runId` уже содержит timestamp + symbolSlug, но мы дублируем
> семантику и в имени PNG — это удобно при копировании/шеринге ссылок на файл.

## Формат имени файла PNG

```
<generatedAt>__<symbolSlug>__<timeframe>__<chartTemplateId>__<kind>.png
```

Где:
- `generatedAt`: UTC, формат `YYYYMMDD-HHmmss`
- `symbolSlug`: например `BTC-USDT` (без `/`)
- `timeframe`: например `1M`, `1w`, `4h`
- `chartTemplateId`: например `ctpl_default_v1`
- `kind`: например `price`, `volume`, `rsi`, `macd`

### Пример

`runs/20251215-102530_BTC-USDT_k3f7a/charts/1M/ctpl_default_v1/20251215-102612__BTC-USDT__1M__ctpl_default_v1__price.png`

## Связь с manifest

- В `ChartsOutputsManifest.items[*].generatedAt` хранится RFC3339 timestamp (UTC).
- Для имени файла `generatedAt` берём тот же момент, но сериализуем в
  `YYYYMMDD-HHmmss` (без `:` и без timezone суффикса).


