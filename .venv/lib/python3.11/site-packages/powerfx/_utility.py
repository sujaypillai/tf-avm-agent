from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

# Load the PowerFx assemblies and types needed for type marshalling from FormulaValue to Python native types.
from powerfx._loader import load

load()

from Microsoft.PowerFx.Types import (  # type: ignore  # noqa: E402
    BlankValue,
    BooleanValue,
    ColorValue,
    DateTimeValue,
    DateValue,
    DecimalValue,
    FormulaValue,
    GuidValue,
    NamedValue,
    NumberValue,
    RecordType,
    RecordValue,
    StringValue,
    TableValue,
    TimeValue,
    VoidValue,
)
from System.Globalization import CultureInfo  # type: ignore # noqa: E402

_invariant = CultureInfo.InvariantCulture
from System import Boolean, DateTime, Guid, TimeSpan  # type: ignore # noqa: E402
from System import Decimal as CsDecimal  # type: ignore # noqa: E402
from System.Threading import CancellationTokenSource  # type: ignore # noqa: E402


def _formulavalue_to_python(val: FormulaValue):
    if val is None:
        return None

    if isinstance(val, BlankValue | VoidValue):
        return None

    if isinstance(val, BooleanValue):
        return bool(val.Value)

    if isinstance(val, StringValue):
        return str(val.Value)

    if isinstance(val, NumberValue):
        return float(val.Value)

    if isinstance(val, DecimalValue):
        return Decimal(str(val.Value))  # convert System.Decimal to Python Decimal via string

    if isinstance(val, DateValue):
        dt = val.Value
        return date(dt.Year, dt.Month, dt.Day)

    if isinstance(val, DateTimeValue):
        dt = val.Value
        return datetime(dt.Year, dt.Month, dt.Day, dt.Hour, dt.Minute, dt.Second, dt.Millisecond * 1000)

    if isinstance(val, TimeValue):
        ts = val.Value
        micros = ts.Milliseconds * 1000
        return time(ts.Hours % 24, ts.Minutes, ts.Seconds, micros)

    if isinstance(val, ColorValue):
        argb = int(val.Value)
        a = (argb >> 24) & 0xFF
        r = (argb >> 16) & 0xFF
        g = (argb >> 8) & 0xFF
        b = (argb >> 0) & 0xFF
        return (r, g, b, a)

    # NEW: GUID → uuid.UUID
    if isinstance(val, GuidValue):
        g = val.Value  # System.Guid
        return UUID(str(g))  # normalize to canonical Python UUID

    if isinstance(val, RecordValue):
        out = {}
        for field in val.Fields:
            out[field.Name] = _formulavalue_to_python(field.Value)

        # Optional: flatten Dataverse-style choice/lookup records
        # if set(out) == {"Label", "Value"}: return out["Label"]
        return out

    if isinstance(val, TableValue):
        rows = []
        for row in val.Rows:
            rows.append(_formulavalue_to_python(row.Value) if row.IsValue else None)
        if rows and all(isinstance(r, dict) and len(r) == 1 for r in rows if r is not None):
            rows = [next(iter(r.values())) if r is not None else None for r in rows]
        return rows

    raise TypeError(f"Unsupported FormulaValue type: {type(val)}")


def _python_to_formulavalue(val) -> FormulaValue:
    """
    Convert Python objects to Power Fx FormulaValue types.

    Raises:
        TypeError: For Record and Table values (not implemented)
        ValueError: For unsupported Python types
    """

    # None -> Blank
    if val is None:
        return FormulaValue.NewBlank()

    # bool before int (since bool is a subclass of int in Python)
    if isinstance(val, bool):
        return FormulaValue.New.__overloads__[Boolean](val)

    # strings
    if isinstance(val, str):
        return FormulaValue.New(val)

    # numeric (int, float) -> Number/Decimal per C# overloads
    if isinstance(val, int | float):
        return FormulaValue.New(val)

    # Python Decimal -> System.Decimal
    if isinstance(val, Decimal):
        return FormulaValue.New(_pydecimal_to_csdecimal(val))

    # date (not datetime): use NewDateOnly to get a DateValue
    if isinstance(val, date) and not isinstance(val, datetime):
        dt = DateTime(val.year, val.month, val.day)
        return FormulaValue.NewDateOnly(dt)

    # datetime -> DateTimeValue (note: tzinfo is ignored; normalize if needed)
    if isinstance(val, datetime):
        # If timezone-aware, normalize as desired (e.g., to UTC) – here we drop tzinfo.
        dt = DateTime(val.year, val.month, val.day, val.hour, val.minute, val.second, val.microsecond // 1000)
        return FormulaValue.New(dt)

    # time -> TimeValue
    if isinstance(val, time):
        ts = TimeSpan(0, val.hour, val.minute, val.second, val.microsecond // 1000)
        return FormulaValue.New(ts)

    # UUID -> GuidValue
    if isinstance(val, UUID):
        guid = Guid.Parse(str(val))
        return FormulaValue.New(guid)

    # Record
    if isinstance(val, dict):
        fields = []
        for k, v in val.items():
            # Keys must be strings for NamedValue. Coerce non-strings via str().
            name = k if isinstance(k, str) else str(k)
            fv = _python_to_formulavalue(v)  # recurse for nested records/primitives
            fields.append(NamedValue(name, fv))
        # list/tuple maps to IEnumerable<NamedValue> seamlessly via pythonnet
        return FormulaValue.NewRecordFromFields(fields)

    if isinstance(val, list):
        # Empty list → empty single-column table "Value"
        if len(val) == 0:
            rec_type = RecordType.Empty()
            return FormulaValue.NewTable(rec_type, [])

        rows: list[RecordValue] = []

        # If all elements are dicts → build multi-column table
        if all(isinstance(x, dict) for x in val):
            for d in val:
                # Each dict → RecordValue
                fields = []
                for k, v in d.items():
                    name = k if isinstance(k, str) else str(k)
                    fv = _python_to_formulavalue(v)
                    fields.append(NamedValue(name, fv))
                rows.append(FormulaValue.NewRecordFromFields(fields))
        else:
            # Otherwise → treat as single-column table with column "Value"
            for item in val:
                fv = _python_to_formulavalue({TableValue.ValueName: item})
                rows.append(fv)

        # Use the type from the first row to define schema
        rec_type = rows[0].Type

        # Build and return TableValue
        return FormulaValue.NewTable(rec_type, rows)

    # Fallback
    raise ValueError(f"Unsupported Python type for conversion to FormulaValue: {type(val)}")


def _pydecimal_to_csdecimal(d: Decimal) -> CsDecimal:
    if not d.is_finite():
        raise ValueError("Non-finite Decimal (NaN/Inf) cannot be converted to Power Fx DecimalValue")

    # Make a culture-invariant, non-exponential string, with <= 28 fractional digits.
    # 'f' removes exponent; then we trim to 28 places and strip trailing zeros.
    s = format(d, "f")  # e.g., '123.45000' or '0.0001234'
    if "." in s:
        i, frac = s.split(".", 1)
        # limit to 28 decimal places (Decimal scale limit in .NET)
        frac = (frac[:28]).rstrip("0")
        s = i if not frac else f"{i}.{frac}"

    # Avoid empty string or lone '-' (shouldn't happen, but guard anyway)
    if s in ("", "-", ".", "-."):
        s = "0"

    # Parse using invariant culture
    return CsDecimal.Parse(s, _invariant)


def _create_cancellation_token(timeout: float | None = None):
    """
    Create a CancellationToken.
    - If timeout is provided, the token cancels automatically after the given seconds.
    - If timeout is None, returns a normal uncancelled token.

    Returns:
        (CancellationTokenSource, CancellationToken)
    """
    cts = CancellationTokenSource()
    if timeout is not None:
        ms = int(timeout * 1000)
        cts.CancelAfter(ms)  # auto-cancel after given ms
    return cts.Token
