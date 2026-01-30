from __future__ import annotations

from typing import Any

from powerfx._loader import load
from powerfx._utility import _create_cancellation_token, _formulavalue_to_python, _python_to_formulavalue

load()
# Import after load so the assemblies are visible.
from Microsoft.PowerFx import (  # type: ignore  # noqa: E402
    CheckResultExtensions,
    ParserOptions,
    ReadOnlySymbolTable,
    ReadOnlySymbolValues,
    RuntimeConfig,
    SymbolTable,
)
from Microsoft.PowerFx import RecalcEngine as _RecalcEngine  # type: ignore  # noqa: E402
from Microsoft.PowerFx.Types import RecordValue  # type: ignore  # noqa: E402
from System import TimeZoneInfo  # type: ignore  # noqa: E402
from System.Globalization import CultureInfo  # type: ignore  # noqa: E402


class Engine:
    """
    Minimal wrapper around Microsoft.PowerFx RecalcEngine.
    - eval(expr: str) -> Python value
    - set(name: str, value: any) to bind variables
    """

    def __init__(self) -> None:
        # Load CLR + PowerFx assemblies first, using dll_dir or env var.

        self._engine = _RecalcEngine()

    def eval(
        self,
        expr: str,
        symbols: dict[str, Any] | None = None,
        timeout: float | None = None,
        timezone: str | None = None,
        locale: str | None = None,
    ) -> Any:
        """
            Evaluate a Power Fx expression and return a Python-native object where possible.
        Optionally pass a dictionary of symbols to bind before evaluation.

        Args:
            expr (str): The Power Fx expression to evaluate.
            symbols (dict[str, Any] | None): Optional dictionary of symbols.
            timeout (float | None): Timeout in seconds. If None, no timeout is applied.
            timezone (str | None): Timezone for this evaluation. If None, defaults to Machine's TZ. https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/default-time-zones?view=windows-11.
            locale (str | None): Locale for this evaluation. If None, defaults to Machine's locale.
        """
        if not isinstance(expr, str):
            raise TypeError("expr must be a string")
        if symbols is not None and not isinstance(symbols, dict):
            raise TypeError("symbols must be a dict[str, Any] or None")

        po = _create_parser_options(timezone, locale)

        sym_vals: ReadOnlySymbolValues | None = None
        if symbols:
            parameter_record_value = _python_to_formulavalue(symbols)  # validate
            if not isinstance(parameter_record_value, RecordValue):
                raise TypeError("symbols must convert to a RecordValue")
            sym_vals = ReadOnlySymbolValues.NewFromRecord(parameter_record_value)

        cancellation_token = _create_cancellation_token(timeout)
        symbol_table: ReadOnlySymbolTable | None = sym_vals.SymbolTable if sym_vals else SymbolTable()
        check = _compile(self, expr, symbol_table, po)  # noqa: F841

        runtime_config = _create_runtime_config(sym_vals, timezone, locale)

        result = CheckResultExtensions.GetEvaluator(check).EvalAsync(cancellation_token, runtime_config).Result
        # returns FormulaValue
        # result = self._engine.EvalAsync(expr, cancellation_token, sym_vals).Result  # returns FormulaValue

        pyResult = _formulavalue_to_python(result)
        return pyResult


def _compile(self, expr: str, symbols: Any | None = None, po: ParserOptions | None = None) -> Any:
    """
    Check/parse an expression once and return a reusable evaluator/runner.
    Raises ValueError with detailed messages if check fails.
    """
    if not isinstance(expr, str):
        raise TypeError("expr must be a string")
    if symbols is not None and not isinstance(symbols, ReadOnlySymbolTable):
        raise TypeError("symbols must be a ReadOnlySymbolTable or None found " + str(type(symbols)))

    check = self._engine.Check(
        expr,
        po,
        symbols,
    )  # returns CheckResult
    if not check.IsSuccess:
        # Build a friendly error message (you can surface spans/severity too)
        msgs = []
        for err in check.Errors:
            # err.Message typically has the human-readable reason
            # err.Span.Min/Max give positions; Severity is usually Error/Warning
            msgs.append("Error " + str(err.Span.Min) + " - " + str(err.Span.Lim) + " : " + str(err.Message))
        raise ValueError("Power Fx failed compilation: " + "; ".join(msgs))

    return check


def _create_parser_options(timezone: str | None, locale: str | None) -> ParserOptions | None:
    if timezone is None and locale is None:
        return None

    po = ParserOptions()

    if timezone is not None:
        po.TimeZone = _to_timezone(timezone)

    if locale is not None:
        po.Culture = _to_culture(locale)
    return po


def _create_runtime_config(
    sym_vals: ReadOnlySymbolValues | None,
    timezone: str | None,
    locale: str | None,
) -> RuntimeConfig:
    runtime_config = RuntimeConfig(sym_vals)

    if timezone is not None:
        runtime_config.AddService[TimeZoneInfo](_to_timezone(timezone))
    if locale is not None:
        runtime_config.AddService[CultureInfo](_to_culture(locale))

    return runtime_config


def _to_culture(locale: str) -> CultureInfo:
    if not locale:
        raise ValueError("Locale/culture string cannot be empty")
    try:
        return CultureInfo(locale)
    except Exception as e:
        raise ValueError(f"Unknown locale/culture: {locale}") from e


def _to_timezone(tz_id: str | None) -> TimeZoneInfo | None:
    if not tz_id:
        raise ValueError("TimeZoneInfo id string cannot be empty")
    try:
        return TimeZoneInfo.FindSystemTimeZoneById(tz_id)
    except Exception as e:
        raise ValueError(f"Unknown TimeZoneInfo id: {tz_id}") from e
