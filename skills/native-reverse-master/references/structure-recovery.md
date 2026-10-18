# Structure Recovery

Load this reference for unknown structs/classes, field offsets, table strides, tagged unions, pointer arrays, or serialization layouts.

## Method

1. Select one allocation, constructor, parser, accessor family, or observed instance.
2. List every read/write as offset, width, signedness, instruction/function, and control-flow condition.
3. Infer alignment and minimum size from the highest evidenced access; do not infer a complete type from one function.
4. Separate embedded objects, pointers, arrays, bitfields, length/capacity pairs, and discriminants.
5. Validate the same candidate layout across at least two independent readers/writers or one static plus one authorized runtime observation.

Use a field ledger:

| Offset | Width | Candidate type | Read evidence | Write evidence | Confidence |
|---|---|---|---|---|---|

For tables, verify stride against multiple records and boundary behavior. For pointers, preserve address space, relocation, endianness, and ownership assumptions. Mark overlaps and conflicting interpretations explicitly.

The deliverable is a bounded layout for the requested subsystem, not a speculative whole-program type database.
