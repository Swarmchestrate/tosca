# Forecast parameters

The `Forecast` policy carries what the [AI
library](https://github.com/Swarmchestrate/ai_library_pip) needs to predict an
application's metrics. Its
[configuration reference](https://github.com/Swarmchestrate/ai_library_pip/blob/v0.1.3/docs/configuration.md)
for v0.1.3 lists the settings that come from the SAT. This page pairs each of
them with the policy field it reads from.

!!! warning ""

    The specification is not entirely finalised or fixed. Field names and types
    may change over the course of the project.

| Policy field | Library setting | Conversion |
| --- | --- | --- |
| `metrics` | `prediction_target` | Direct |
| `resolution` | `data_frequency` | Seconds to a duration string |
| `forecast_duration` | `horizon` | `forecast_duration / resolution` steps |
| `lookback_duration` | `window` | `lookback_duration / resolution` steps |
| `history_duration` | `parquet_train_size` | `history_duration / resolution` rows |
| `retrain_interval` | `retrain_frequency` | Lowered to a supported cadence |
| `coverage` | `conf_q_alpha` | `1 - coverage` |
| `pipeline` | `pipeline_type` | Direct |
| *monitoring* | `STANDARD_METRICS` | Every metric the targets declare |
| *monitoring* | `poll_interval_seconds` | The finest collection frequency, capped at `resolution` |

A SAT states periods in seconds. `get_forecast()` does the arithmetic and
returns the settings above, flooring step and row counts to a minimum of one.
The last two are read from the monitoring declarations of the policy's targets.
