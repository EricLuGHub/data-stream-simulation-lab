# Trial 6: Wall-Mid Take Then Make

Approach:
- Uses a wall-mid fair proxy from higher-volume levels instead of only top-of-book.
- Two-stage execution: first take obvious edge, then make around fair.
- One-tick quote improvement is allowed only when still on the profitable side of fair.
- Uses inventory flattening around fair when position drifts beyond +/-30.

Rationale:
- Strongly inspired by successful Rainforest Resin styles, adapted to ASH without hard-coding a fixed fair value.
- Keeps behavior simple and robust to avoid overfitting.
