# Именование изображений графиков (prototype)

Цель: чтобы по **одному пути PNG в GCS** было понятно:

- когда сгенерировали
- по какому символу
- какой таймфрейм
- какой шаблон (`chartTemplateId`)

`kind` **не включаем в имя файла PNG**: в MVP `1 request -> 1 PNG` на каждый
`chartTemplateId`, а “вид” изображения хранится в manifest’е
(`ChartsOutputsManifest.items[*].kind`) и берётся из `chartTemplate.description`.

## Директория

PNG для каждого запроса шага записываются в директорию:

`charts/<runId>/<stepId>/`

> Примечание: `runId` уже содержит timestamp + symbolSlug, но мы дублируем
> семантику и в имени PNG — это удобно при копировании/шеринге ссылок на файл.

## Формат имени файла PNG

```
<generatedAt>_<symbolSlug>_<timeframe>_<chartTemplateId>.png
```

Где:
  - `generatedAt`: UTC, формат `YYYYMMDD-HHmmss`
  - `symbolSlug`: например `BTCUSDT` (из `scope.symbol`)
- `timeframe`: например `1M`, `1w`, `4h`
- `chartTemplateId`: например `ctpl_price_ma1226_vol_v1`

### Пример

`charts/20251215-102530_BTCUSDT_k3f7a/charts:1M:ctpl_price_ma1226_vol_v1/20251215-102612_BTCUSDT_1M_ctpl_price_ma1226_vol_v1.png`

## Связь с manifest

- В `ChartsOutputsManifest.items[*].generatedAt` хранится RFC3339 timestamp (UTC).
- Для имени файла `generatedAt` берём тот же момент, но сериализуем в
  `YYYYMMDD-HHmmss` (без `:` и без timezone суффикса).
