# T-021: Project README (root)

## Summary

- Добавить подробный `README.md` в корень репозитория, описывающий назначение сервиса worker_chart_export, архитектуру, конфигурацию, хранилища, тестирование, деплой и известные ограничения.

## Goal

- Дать новой команде и ревьюерам единое входное описание сервиса без необходимости читать все таски и спецификации.

## Scope

- Структурированный README с разделами: Overview, Быстрый старт (локально), Архитектура обработки, Конфигурация (env), Хранилища (Firestore/GCS), CLI (статус), Тестирование, Деплой (статус), Обсервабилити (статус), Известные ограничения, Ссылки на спецификации.
- README не меняет содержимое @docs-general и @docs-gcp; опирается на их требования.
- Учитывает решения по gs://, timezone `Etc/UTC`, обязательный `chartImgSymbolTemplate`, правила PNG naming и manifest.

## Planned Scenarios (TDD)

### Scenario 1: README покрывает ключевые разделы

**Prerequisites**
- Нет
- Requires human-in-the-middle: NO

**Steps**
1) Открыть корневой `README.md`.
2) Проверить наличие всех разделов из Scope.

**Expected result**
- Все разделы присутствуют и содержат актуальные выдержки из спецификаций/тасков.

### Scenario 2: README отражает текущие ограничения и TODO

**Prerequisites**
- Нет
- Requires human-in-the-middle: NO

**Steps**
1) Проверить блок “Известные ограничения”.

**Expected result**
- Перечислены ключевые ограничения: не реализованный core (до T-009), отсутствие интеграционного harness (T-017/T-020), архитектурный выравнивание символов (T-019) и др.

### Scenario 3: README указывает ссылки на спецификации

**Prerequisites**
- Нет
- Requires human-in-the-middle: NO

**Steps**
1) Проверить список ссылок на `docs-worker-chart-export/*`, `docs-general/*`, `docs-gcp/*`.

**Expected result**
- Ссылки присутствуют, читаемы, не противоречат запретам на правки @docs-general/@docs-gcp.

## Acceptance Criteria

- В корне создан `README.md` с разделами из Scope.
- README согласован с актуальными контрактами (gs://, PNG naming без kind, timezone `Etc/UTC`, chartImgSymbolTemplate обязателен).
- Не содержит секретов и не требует правок в @docs-general/@docs-gcp.

## Risks

- Устаревание информации при будущих тасках (нужно обновлять при интеграции T-009+).

## Verify Steps

- Ручная проверка сценариев 1–3.

## Rollback Plan

- Удалить файл `README.md` и откатить коммит.
