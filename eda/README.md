# EDA: задачи Codeforces для AlgoMind

Исследован `default/test` из [open-r1/codeforces](https://huggingface.co/datasets/open-r1/codeforces) - это 468 задач периода 2024 — 2025 года. В `default/train` по метаданным ещё 9 556 строк. `test` будет использоваться только для разведочного анализа, не для настройки модели или базы практики.

## Воспроизведение

Нужны Python 3.11+, сеть и `pyarrow` (при анализе 26.0.1). Исходные данные не копируются в репозиторий. Из каталога `algomind`:

```bash
python -m venv /tmp/algomind-eda
/tmp/algomind-eda/bin/pip install pyarrow==26.0.1
curl -L --fail -o /tmp/codeforces-test.parquet https://huggingface.co/datasets/open-r1/codeforces/resolve/fbe3f6e903ee854eec2e69e9d96d0306cde59baf/data/test-00000-of-00001.parquet
/tmp/algomind-eda/bin/python eda/analyze.py /tmp/codeforces-test.parquet > /tmp/algomind-results.json
diff -u eda/results.json /tmp/algomind-results.json
```

SHA-256 файла: `f3e241f6a111822aed1ee6800d3d3f73917ea4d10e70e264b47a7bcdba4cbf31`. Скрипт проверяет число строк и полей; `diff` проверяет хеш и все результаты. В [results.json](results.json) — полные распределения и пропуски по всем 27 полям. Под пропуском считаем `null`, пустую строку или список; ноль и `false` не пропуски. Пустые необязательные поля не обязательно ошибки.

## Состав и качество

Поля объединяются в идентификацию и сведения о соревновании (`id`, `aliases`, `contest_id`, `contest_name`, `contest_type`, `contest_start`, `contest_start_year`, `index`), условие и ограничения (`title`, `description`, `input_format`, `output_format`, `interaction_format`, `note`, `examples`, `time_limit`, `memory_limit`), разметку (`rating`, `tags`, `editorial`) и проверку (`testset_size`, `official_tests`, `official_tests_complete`, `input_mode`, `generated_checker`, `executable`, `generated_tests`).

- `id`, `title`, `description` заполнены во всех строках. Повторных `id` и полных совпадений `description` после нормализации пробельных символов нет.
- Нет `rating` у 10 (2,1%), тегов у 5 (1,1%), `input_format` у 4, `output_format` у 15, примеров у 1, `editorial` у 208 (44,4%).
- Только у 21 (4,5%) `official_tests_complete=true`, у 447 набор официальных тестов неполон. У 448 `executable=true`, по определению авторов это прохождение имеющихся тестов хотя бы тремя решениями, а не доказательство полноты тестов или корректности любых решений.

## Распределения

Каждый `█` ≈ 5 задач, округление до ближайшего целого; числа справа точные. Рейтинг — исходный числовой рейтинг, пропуски показаны отдельно.

```text
800–1199   ███████████████████████  116
1200–1599  ██████████████            71
1600–1999  ██████████████            71
2000–2399  █████████████             63
2400–2799  ██████████                51
2800–3199  █████████                 44
3200–3599  ████████                  42
нет        ██                        10
```

Низкий диапазон 800–1199 содержит 116 задач (24,8% всех строк), сложность остального набора широка. Для пилота нужно отдельно отбирать и проверять доступные участникам задачи, не считать этот диапазон готовой калибровкой.

Топ-10 тегов; одна задача может иметь несколько тегов, поэтому суммы больше 468:

```text
greedy                  ██████████████████████████████████████████████ 228
math                    ████████████████████████████████████████       200
dp                      ███████████████████████████                    137
implementation          ███████████████████████████                    135
brute force             ███████████████████████████                    134
data structures         █████████████████████████                        127
constructive algorithms █████████████████████                           105
binary search           █████████████████                                84
graphs                  ████████████                                     61
sortings                ████████████                                     60
```

Частоты сильно различаются, для оценки классификатора нужны метрики по отдельным тегам и отдельная проверка редких тем.
