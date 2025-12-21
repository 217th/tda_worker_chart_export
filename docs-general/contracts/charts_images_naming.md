# Именование изображений графиков (prototype)

Цель: чтобы по **одному пути PNG в GCS** было понятно:

- когда сгенерировали
- по какому символу
- какой таймфрейм
- какой шаблон

## Директория

Для единообразия с manifest'ом:

`charts/<runId>/<stepId>/`

> Примечание: `runId` уже содержит timestamp + symbolSlug, но мы дублируем
> семантику и в имени PNG — это удобно при копировании/шеринге ссылок на файл.

## Формат имени файла PNG

```
<generatedAt>_<symbolSlug>_<timeframe>_<chartTemplateId>.png
```

Где:
- `generatedAt`: UTC, формат `YYYYMMDD-HHmmss`
- `symbolSlug`: например `BTC-USDT` (без `/`)
- `timeframe`: например `1M`, `1w`, `4h`
- `chartTemplateId`: например `ctpl_default_v1`

### Пример

`charts/20251215-102530_BTC-USDT_k3f7a/charts:1M:ctpl_default_v1/20251215-102612_BTC-USDT_1M_ctpl_default_v1.png`

## Связь с manifest

- В `ChartsOutputsManifest.items[*].generatedAt` хранится RFC3339 timestamp (UTC).
- Для имени файла `generatedAt` берём тот же момент, но сериализуем в
  `YYYYMMDD-HHmmss` (без `:` и без timezone суффикса).


