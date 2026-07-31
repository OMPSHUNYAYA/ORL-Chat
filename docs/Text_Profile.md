# ORL-Chat v2.0.0 Text Profile

## Profile

`ORL-CHAT-UNICODE-SCALAR-EXACT-2-D01`

## Contract

ORL-Chat preserves every admitted string as an exact Unicode code-point sequence.

`same code points -> same string identity`

`different code points -> different string identity`

No runtime NFC normalization, case folding, compatibility normalization, transliteration, grapheme comparison, or visual-equivalence rule is applied.

`"café" != "cafe\u0301"`

Both forms can be admitted, but they remain distinct.

## Frozen Boundary-Whitespace Rule

Identifier admission does not call runtime `strip()` or `trim()` behavior. Leading or trailing code points are checked against this explicit table:

- `U+0009..U+000D`
- `U+0020`
- `U+0085`
- `U+00A0`
- `U+1680`
- `U+2000..U+200A`
- `U+2028..U+2029`
- `U+202F`
- `U+205F`
- `U+3000`

An identifier beginning or ending with one of these code points is refused. The table is fixed by the text profile and does not change with the host runtime.

## Frozen Rejection Table

The text profile uses explicit code-point tests rather than runtime Unicode categories.

Identifiers refuse:

- `U+0000..U+001F`
- `U+007F..U+009F`
- `U+D800..U+DFFF`
- `U+00AD`
- `U+0600..U+0605`
- `U+061C`
- `U+06DD`
- `U+070F`
- `U+0890..U+0891`
- `U+08E2`
- `U+180E`
- `U+200B..U+200F`
- `U+202A..U+202E`
- `U+2060..U+2064`
- `U+2066..U+206F`
- `U+FEFF`
- `U+FFF9..U+FFFB`
- `U+110BD`
- `U+110CD`
- `U+13430..U+1343F`
- `U+1BCA0..U+1BCA3`
- `U+1D173..U+1D17A`
- `U+E0001`
- `U+E0020..U+E007F`

Presentation and declared-value strings permit `U+0009` and `U+000A`. They refuse `U+000D` and the remaining listed control, format, and surrogate code points.

## Cross-Implementation Binding

The same table is implemented directly in:

- The Python reference kernel.
- The independent Python verifier.
- The JavaScript resolver.

The cross-language parity manifest declares the text-profile identity. The shipped Unicode-sensitive vectors verify a decomposed exact sequence, an astral-plane object key, deterministic refusal of frozen boundary whitespace, and deterministic refusal of a frozen format character.

## Integration Rule

An upstream system may normalize or transform text only as a separately declared operation before ORL-Chat intake. The transformed code points then become the submitted evidence.

Changing this table or any exact-sequence rule defines a new text profile and requires regenerated corpora, vectors, receipts, and verification results.
