# Multiplier_Example

## Introduction

`mult_16_bit` is an AXI4-Lite IP that multiplies two 16-bit unsigned operands (`A_REG`, `B_REG`) and returns a 32-bit product (`PROD_REG`) 3 clocks after either operand changes. Writing `CTRL_REG.CLEAR` clears both operands.

The register map is described in `mult_16_bit.json` and rendered to HTML with `regmap_gen.py`.

## Register Map Generation

Requires Python 3 (standard library only).

```sh
python regmap_gen.py mult_16_bit.json                # -> mult_16_bit_register_map.html
python regmap_gen.py mult_16_bit.json -o docs/       # -> docs/mult_16_bit_register_map.html
python regmap_gen.py mult_16_bit.json --no-autofill  # don't auto-fill unused bits as RESERVED
```

The output is named `<ip_name>_register_map.html`.

### JSON Format

```json
{
  "title": "16-Bit Multiplier AXI-Lite IP",
  "ip_name": "mult_16_bit",
  "intro": "Multiplies two 16-bit unsigned operands.",
  "access_types": {
    "RW": "Read/write",
    "RO": "Read-only"
  },
  "registers": [
    {
      "name": "Operand A Register",
      "short_name": "A_REG",
      "offset": "0x00",
      "alias": "slv_reg0",
      "fields":
      [
        { "name": "A",
          "bits": "[15:0]",
          "access": "RW",
          "reset": "0x0000",
          "description": "Multiplier operand A (unsigned)."
        }
      ]
    },
    {
      "type": "reserved",
      "name": "Reserved",
      "offset": "0x10",
      "offset_end": "0x3C",
      "description": "Unused."
    }
  ]
}
```

- `bits`: `"[15:0]"`, `"[0]"`, `"15:0"`, or `[15, 0]`.
- `reset`: number or string (`"0"`, `"0x1F"`, `"0x0000_0000"`); defaults to `0`.
- Unlisted bits are documented as `RESERVED`.
- The script exits with an error on overlapping bits, duplicate offsets, or resets that don't fit the field.

See the comment block at the top of `regmap_gen.py` for all options.
