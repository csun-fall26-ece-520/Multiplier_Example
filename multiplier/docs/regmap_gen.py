#!/usr/bin/env python3
"""
regmap_gen.py - Generate an HTML AXI register map from a JSON description.

Output file:
    <design_name>_register_map.html, where <design_name> is "ip_name" from the
    JSON (or the JSON file name if "ip_name" is missing). By default it is
    written next to the JSON file; -o can point to a folder or a full file name.

Usage:
    python regmap_gen.py mult_16_bit.json                # -> mult_16_bit_register_map.html
    python regmap_gen.py mult_16_bit.json -o docs/       # -> docs/mult_16_bit_register_map.html
    python regmap_gen.py mult_16_bit.json -o out.html    # -> out.html
    python regmap_gen.py mult_16_bit.json --no-autofill  # don't auto-add RESERVED fields

JSON format (see mult_16_bit.json for a full example).
The // comments below are for explanation only; real JSON can't contain them.

{
  "title": "16-Bit Multiplier AXI-Lite IP",   // page heading
  "ip_name": "mult_16_bit",                   // design name: used in the heading and output file name
  "data_width": 32,                           // optional, default 32
  "intro": "Multiplies two 16-bit ...",       // optional description of the design
  "access_types": {                           // optional, shown as a table under the intro;
    "RW": "Read/write",                       // defaults to RW / RO / WO if omitted
    "RO": "Read-only",
    "WO": "Write-only (self-clearing, reads return 0)"
  },
  "registers": [
    {
      "name": "Operand A Register",
      "short_name": "A_REG",                  // optional, shown as [A_REG]
      "offset": "0x00",                       // hex string or int
      "alias": "slv_reg0",                    // optional, shown next to the offset
      "reset": "0x0000_0000",                 // optional, computed from field resets if omitted
      "fields":
      [
        { "name": "A",
          "bits": "[15:0]",
          "access": "RW",                     // a code from access_types (default RW)
          "reset": "0x0000",                  // optional, default 0
          "description": "Multiplier operand A (unsigned)."
        }
      ]
    },
    {
      "type": "reserved",                     // an unused address range, no fields
      "name": "Reserved",
      "alias": "slv_reg4 – slv_reg15",
      "offset": "0x10",
      "offset_end": "0x3C",
      "description": "Unused. Read/write with no function."
    }
  ]
}

Field "bits" may be "[15:0]", "15:0", "[3]", "3", 3, or [15, 0].
Field "reset" may be a number or a string such as "0", "0x1F" or "0x0000_0000";
it is always re-formatted for the page based on the field width.
Bits not covered by any field are filled with RESERVED fields unless --no-autofill.
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path

CSS = """\
    body { font-family: Arial; margin: 24px; }
    h1 { margin-bottom: 20px; }
    .reg { margin-bottom: 40px; }
    .meta { color: #555; margin-bottom: 8px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #333; padding: 8px; }
    th { background: #e5e5e5; text-align: left; }
    .bitgrid { table-layout: fixed; }
    .bitgrid td {
      text-align: center;
      font-family: monospace;
      background: #f2f2f2;
      font-weight: 600;
    }
    .bitgrid td.narrow { padding: 8px 2px; font-size: 10px; }
    .mono { font-family: monospace; }
    .legend { width: auto; margin-bottom: 40px; }
    .legend td:first-child { font-family: monospace; font-weight: 600; }"""

# Used when the JSON has no "access_types" entry.
DEFAULT_ACCESS_TYPES = {
    "RW": "Read/write",
    "RO": "Read-only",
    "WO": "Write-only (self-clearing, reads return 0)",
}

NARROW_WIDTH = 3  # fields this many bits or fewer get the compact style


class RegMapError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def esc(s):
    return html.escape(str(s), quote=True)


def parse_int(value, what):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip().replace("_", "").lower()
        try:
            return int(s, 0)
        except ValueError:
            pass
    raise RegMapError(f"Cannot parse {what}: {value!r}")


def parse_bits(bits, where):
    """Return (msb, lsb)."""
    if isinstance(bits, int):
        return bits, bits
    if isinstance(bits, list) and len(bits) in (1, 2):
        msb, lsb = (bits[0], bits[-1])
        return int(msb), int(lsb)
    if isinstance(bits, str):
        m = re.fullmatch(r"\s*\[?\s*(\d+)\s*(?::\s*(\d+)\s*)?\]?\s*", bits)
        if m:
            msb = int(m.group(1))
            lsb = int(m.group(2)) if m.group(2) is not None else msb
            return msb, lsb
    raise RegMapError(f"{where}: invalid bits spec {bits!r}")


def bits_label(msb, lsb):
    return f"[{msb}]" if msb == lsb else f"[{msb}:{lsb}]"


def fmt_hex(value, width_bits):
    """0x0000 / 0x0000_0000 style, digits grouped by 4."""
    digits = max(1, (width_bits + 3) // 4)
    h = f"{value:0{digits}X}"
    if digits > 4:
        groups = []
        while h:
            groups.insert(0, h[-4:])
            h = h[:-4]
        h = "_".join(groups)
    return "0x" + h


def fmt_field_reset(value, width):
    if width == 1:
        return str(value)
    return fmt_hex(value, width)


def fmt_offset(value):
    return f"0x{value:02X}"


# ---------------------------------------------------------------- model
def normalize_register(reg, data_width, autofill, idx):
    where = f"register #{idx} ({reg.get('name', '?')})"
    if "offset" not in reg:
        raise RegMapError(f"{where}: missing 'offset'")
    out = dict(reg)
    out["offset"] = parse_int(reg["offset"], f"{where} offset")

    if reg.get("type") == "reserved":
        if "offset_end" in reg:
            out["offset_end"] = parse_int(reg["offset_end"], f"{where} offset_end")
        return out

    fields = []
    for f in reg.get("fields", []):
        fname = f.get("name")
        if not fname:
            raise RegMapError(f"{where}: field without a name")
        msb, lsb = parse_bits(f.get("bits"), f"{where} field {fname}")
        if msb < lsb:
            msb, lsb = lsb, msb
        if msb >= data_width:
            raise RegMapError(f"{where} field {fname}: bit {msb} exceeds data width {data_width}")
        width = msb - lsb + 1
        reserved = f.get("reserved", fname.upper() == "RESERVED")
        reset_raw = f.get("reset", 0)
        reset_val = parse_int(reset_raw, f"{where} field {fname} reset")
        if reset_val >= (1 << width):
            raise RegMapError(f"{where} field {fname}: reset {reset_raw!r} doesn't fit in {width} bits")
        fields.append({
            "name": fname, "msb": msb, "lsb": lsb, "width": width,
            "access": f.get("access", "–" if reserved else "RW"),
            "reset": reset_val,
            "reset_text": "0" if reserved and reset_val == 0 else fmt_field_reset(reset_val, width),
            "description": f.get("description", "Reserved. Reads as 0." if reserved else ""),
            "reserved": reserved,
        })

    # overlap check
    used = {}
    for f in fields:
        for b in range(f["lsb"], f["msb"] + 1):
            if b in used:
                raise RegMapError(f"{where}: bit {b} used by both {used[b]} and {f['name']}")
            used[b] = f["name"]

    # fill gaps with RESERVED
    if autofill:
        b = data_width - 1
        while b >= 0:
            if b in used:
                b -= 1
                continue
            hi = b
            while b >= 0 and b not in used:
                b -= 1
            lo = b + 1
            w = hi - lo + 1
            fields.append({
                "name": "RESERVED", "msb": hi, "lsb": lo, "width": w,
                "access": "–", "reset": 0, "reset_text": "0",
                "description": "Reserved. Reads as 0.", "reserved": True,
            })

    fields.sort(key=lambda f: f["msb"], reverse=True)
    out["fields"] = fields

    computed = sum(f["reset"] << f["lsb"] for f in fields)
    if "reset" in reg:
        given = parse_int(reg["reset"], f"{where} reset")
        if given != computed and fields:
            print(f"warning: {where}: reset {fmt_hex(given, data_width)} differs from "
                  f"field resets {fmt_hex(computed, data_width)}", file=sys.stderr)
        out["reset_val"] = given
    else:
        out["reset_val"] = computed
    return out


def load_map(path, autofill):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    dw = int(data.get("data_width", 32))
    regs = [normalize_register(r, dw, autofill, i) for i, r in enumerate(data.get("registers", []))]

    seen = {}
    for r in regs:
        if r.get("type") == "reserved":
            continue
        if r["offset"] in seen:
            raise RegMapError(f"offset {fmt_offset(r['offset'])} used by both "
                              f"{seen[r['offset']]} and {r.get('name')}")
        seen[r["offset"]] = r.get("name")
    data["registers"] = regs
    data["data_width"] = dw
    return data


# ---------------------------------------------------------------- render
def render_bitgrid(fields, data_width):
    cells = []
    next_bit = data_width - 1  # walk MSB -> LSB; pad any gaps with blank cells
    for f in fields:
        if f["msb"] < next_bit:
            cells.append(f'      <td colspan="{next_bit - f["msb"]}">&nbsp;</td>')
        cls_attr = ' class="narrow"' if f["width"] <= NARROW_WIDTH else ""
        cells.append(f'      <td colspan="{f["width"]}"{cls_attr}>'
                     f'{esc(f["name"])} {bits_label(f["msb"], f["lsb"])}</td>')
        next_bit = f["lsb"] - 1
    if next_bit >= 0:
        cells.append(f'      <td colspan="{next_bit + 1}">&nbsp;</td>')
    return ('  <table class="bitgrid">\n    <tr>\n'
            + "\n".join(cells) + "\n    </tr>\n  </table>")


def render_field_table(fields):
    rows = ["""  <table>
    <tr>
      <th>Field</th>
      <th>Bits</th>
      <th>Access</th>
      <th>Reset</th>
      <th>Description</th>
    </tr>"""]
    for f in fields:
        rows.append(f"""    <tr>
      <td class="mono">{esc(f["name"])}</td>
      <td class="mono">{bits_label(f["msb"], f["lsb"])}</td>
      <td>{esc(f["access"])}</td>
      <td class="mono">{esc(f["reset_text"])}</td>
      <td>{esc(f["description"])}</td>
    </tr>""")
    rows.append("  </table>")
    return "\n".join(rows)


def render_register(r, dw):
    if r.get("type") == "reserved":
        alias = f' [{esc(r["alias"])}]' if r.get("alias") else ""
        off = fmt_offset(r["offset"])
        if "offset_end" in r:
            off += " – " + fmt_offset(r["offset_end"])
        desc = r.get("description", "Reserved.")
        return f"""<div class="reg">
  <h2 class="mono">{esc(r.get("name", "Reserved"))}{alias}</h2>
  <div class="meta mono">Offset: {off}</div>
  <p>{esc(desc)}</p>
</div>"""

    short = f' [{esc(r["short_name"])}]' if r.get("short_name") else ""
    alias = f' ({esc(r["alias"])})' if r.get("alias") else ""
    comment = f'<!-- {esc(r.get("name", ""))} -->\n'
    desc = f'  <p>{esc(r["description"])}</p>\n' if r.get("description") else ""
    return f"""{comment}<div class="reg">
  <h2 class="mono">{esc(r.get("name", ""))}{short}</h2>
  <div class="meta mono">Offset: {fmt_offset(r["offset"])}{alias} &nbsp; Reset: {fmt_hex(r["reset_val"], dw)}</div>
{desc}
{render_bitgrid(r["fields"], dw)}

{render_field_table(r["fields"])}
</div>"""


def render_access_table(access_types):
    rows = ["""<h2>Access Types</h2>
<table class="legend">
  <tr>
    <th>Access</th>
    <th>Description</th>
  </tr>"""]
    for code, desc in access_types.items():
        rows.append(f"""  <tr>
    <td>{esc(code)}</td>
    <td>{esc(desc)}</td>
  </tr>""")
    rows.append("</table>")
    return "\n".join(rows)


def render_html(data):
    title = data.get("title", "Register Map")
    ip = data.get("ip_name")
    heading = f"AXI Register Map: {title}" + (f" ({ip})" if ip else "")
    intro = data.get("intro")
    access_types = data.get("access_types", DEFAULT_ACCESS_TYPES)
    regs = sorted(data["registers"], key=lambda r: r["offset"])

    # warn about access codes used in fields but missing from the table
    used = {f["access"] for r in regs if r.get("type") != "reserved"
            for f in r["fields"] if not f["reserved"]}
    for code in sorted(used - set(access_types)):
        print(f"warning: access type {code!r} is used but not listed in access_types",
              file=sys.stderr)

    body = "\n\n".join(render_register(r, data["data_width"]) for r in regs)
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{esc(title)} Register Map</title>
  <style>
{CSS}
  </style>
</head>

<body>

<h1>{esc(heading)}</h1>
{f"<p>{esc(intro)}</p>" if intro else ""}

{render_access_table(access_types) if access_types else ""}

{body}

</body>
</html>
"""


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate an HTML register map from JSON.")
    ap.add_argument("json_file", help="input register description (.json)")
    ap.add_argument("-o", "--output",
                    help="output .html file or directory "
                         "(default: <ip_name>_register_map.html next to the JSON)")
    ap.add_argument("--no-autofill", action="store_true",
                    help="don't add RESERVED fields for unused bits")
    args = ap.parse_args(argv)

    try:
        data = load_map(args.json_file, autofill=not args.no_autofill)
    except (RegMapError, json.JSONDecodeError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    design = data.get("ip_name") or Path(args.json_file).stem
    default_name = f"{design}_register_map.html"
    if args.output is None:
        out = Path(args.json_file).parent / default_name
    elif Path(args.output).is_dir():
        out = Path(args.output) / default_name
    else:
        out = Path(args.output)
    out.write_text(render_html(data), encoding="utf-8")
    n = sum(1 for r in data["registers"] if r.get("type") != "reserved")
    print(f"Wrote {out} ({n} registers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
